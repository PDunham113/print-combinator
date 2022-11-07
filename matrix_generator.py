from collections import namedtuple
import argparse
import json

Test = namedtuple("Test", [
    "name",
    "base_name",
    "cnd",
    "batch",
    "machine",
    "sample",
    "print_time",
    "print_materials",
    "print_max_samples",
])


def _concat_name(base=None, ext=None):
    """Helper for generating test names

    When given two arguments, <ext> is appended to <base> via a hyphen. If
    given only one argument, that argument is returned by itself.

    @param base String to be appended to
    @param ext String to append

    @returns Generated string
    """
    strs = []

    if base is not None:
        strs.append(base)
    if ext is not None:
        strs.append(ext)

    return '-'.join(strs)


def matrix_to_list(matrix, test_name=None):
    """Create list of tests from a test matrix encoded as nested dictionaries.

    Tests are encoded as a series of nested dictionaries with the deepest level
    containing a dictionary with the "print-material" and "print-time" keys, as
    well as a number of environmental condition keys.
    TODO: Explain this better, somewhere.

    This function searches for "print-material" and "print-time" by searching
    through the dictionary tree. Each test name is generated by concatenating
    all the keys in the branch of the tree, separated by underscores. A list of
    tuples is retuned, with each tuple containing the test name, print time,
    and cc of each material specified.

    @param matrix Dictionary representing test matrix
    @param test_name Original test name string, if applicable

    @returns List of all tests defined in matrix
    """
    test_list = []

    for key in matrix:
        print('Checking {}'.format(key))
        print('Test is now named {}'.format(_concat_name(test_name, key)))
        try:
            if 'print-material' in matrix[key] and 'print-time' in matrix[key]:
                print('Found base test!')
                test_list.extend(tests_to_list(
                    matrix[key], _concat_name(test_name, key)
                ))
            else:
                print('No base, recursing')
                print('Passing along {}'.format(test_name))
                test_list.extend(matrix_to_list(
                    matrix[key], _concat_name(test_name, key)
                ))
        except TypeError:
            print('{} missing metadata!'.format(test_name))
            continue

    return test_list


def tests_to_list(matrix, test_name):
    """Create list of tests from a base test matrix object.

    Turns a properly-formatted base test matrix object into a list of tests.

    A properly formatted base test matrix object looks like the following:
    ```
    {
        "print-material": {<mat>: <qty>, <mat>: <qty>, ...},
        "print-time": <time>
        <cnd>: {"B": <num-batches>, "M": <num-machines>, "S": <num-samples},
        <cnd>: {"B": <num-batches>, "M": <num-machines>, "S": <num-samples},
        ...
    }
    ```
    and will return a list that looks like this:
    ```
    [
        (<test>-<cnd>-<batch>-<machine>-<sample>, <time>, {<mat>: <qty>, ...}),
        (<test>-<cnd>-<batch>-<machine>-<sample>, <time>, {<mat>: <qty>, ...}),
        (<test>-<cnd>-<batch>-<machine>-<sample>, <time>, {<mat>: <qty>, ...}),
        ....
    ]

    Samples may optionally specify a "print_max_samples" field, denoting how
    many samples can fit into a single printable part. If not present, this
    field will be set to one

    @param matrix Dictionary containing test
    @param test_name Name of test

    @returns List of test tuples
    """
    materials = {}
    test_list = []

    print_time = matrix.pop('print-time')
    for mat, qty in matrix.pop('print-material').items():
        materials[mat] = qty
    print_max_samples = matrix.pop('print-max-samples', 1)

    for cnd in matrix:
        for batch in range(matrix[cnd]['B']):
            for machine in range(matrix[cnd]['M']):
                for sample in range(matrix[cnd]['S']):
                    full_test = '{}-{}-B{}-M{}-S{}'.format(
                        test_name, cnd, batch, machine, sample)
                    test_list.append(Test(
                        name=full_test,
                        base_name=test_name,
                        cnd=cnd,
                        batch=batch,
                        machine=machine,
                        sample=sample,
                        print_time=print_time,
                        print_max_samples=print_max_samples,
                        print_materials=materials,
                    ))

    return test_list


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generates list of tests from test matrix JSON'
    )

    parser.add_argument('test_matrix', help='File containing test matrix JSON')
    parser.add_argument('output', default='test-list.csv', nargs='?',
                        help='Name of file to store output CSV to')

    args = parser.parse_args()

    # Load matrix
    with open(args.test_matrix, 'r') as test_matrix_file:
        test_matrix = json.load(test_matrix_file)
    # Parse
    test_list = matrix_to_list(test_matrix)
    # Store list
    with open(args.output, 'w') as test_list_file:
        for test in test_list:
            test_list_file.write(','.join((
                test.name,
                str(test.print_time),
                *[str(value) for key, value in test.print_materials.items()]
            )))
            test_list_file.write('\n')