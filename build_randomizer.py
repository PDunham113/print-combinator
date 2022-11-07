from datetime import timedelta
import argparse
import json
import random

import matrix_generator

BATCH_MAP = ('"A"', '"B"', '"C"')
MACHINE_MAP = ('"1"', '"2"')
SAMPLE_MAP = ('1', '2', '3', '4', '5')


class Build(object):
    """Represents the contents of an Eiger build"""

    def __init__(self, name, batch=None, machine=None, max_material={'CFA': 50, 'OFA': 800}):
        """Create a Build object

        @param name Unique identifier to be used for this build
        @param batch
        """
        self.name = name
        self.max_material = max_material

        self._parts = {}
        self._print_time = 0
        self._print_materials = {}

        # One-time write variables
        self._batch = batch
        self._machine = machine
        self._first_part = True  # Used to ignore checks on first add

    def __repr__(self):
        """Long string representation.

        Returns a printable list of all parts in build, e.g:
        ```
        2x D6641-ZX-PF (RTW-1, ETD-3)
        1x D256-XY-FF (RTD-1)
        ```
        """
        parts = []

        for base_name in self._parts:
            num_parts = len(self._parts[base_name])
            cnds = ','.join([
                '{}-{}'.format(part.cnd, SAMPLE_MAP[part.sample])
                for part in self._parts[base_name].values()
            ])
            parts.append('{}x {} ({})'.format(num_parts, base_name, cnds))

        return '\n'.join(parts)

    def __str__(self):
        """Short string representation"""
        return self.name

    def add_part(self, part, ignore_checks=False):
        """Adds a part to build, if possible

        Checks build's constraints (typically max material, machine & batch
        ID), and if all is allowed, adds part to build.

        Machine & batch ID are set if not already, material & print time
        counters are incremented

        @param part Test tuple containing name & part metadata
        @param ignore_checks True if checks should be ignored. Default False

        @raises RuntimeError if part could not be added
        """
        if self._batch is None:
            self._batch = part.batch
        if self._machine is None:
            self._machine = part.machine
        if self._first_part:
            self._first_part = False
            ignore_checks = True

        # Check batch & machine ID - they must match
        if self._batch != part.batch and not ignore_checks:
            print(ignore_checks)
            raise RuntimeError('Part did not match Build batch ID')
        if self._machine != part.machine and not ignore_checks:
            raise RuntimeError('Part did not match Build machine ID')

        # Seed the internal part list
        try:
            self._parts[part.base_name]
        except KeyError:
            self._parts[part.base_name] = {}

        # Check if we're already in here
        if part.cnd in self._parts[part.base_name] and not ignore_checks:
            raise RuntimeError('Part already in build')
        if len(self._parts[part.base_name]) % part.print_max_samples == 0:
            # Check material constraints
            for key in part.print_materials:
                if (((self.print_materials.get(key, 0)
                      + part.print_materials[key])
                          > self.max_material.get(key, 0))
                      and not ignore_checks):
                   raise RuntimeError('Part uses too much {}'.format(key))
            # If we're here, we're adding the part. We only add material once
            # per print_max_samples
            self._print_time += part.print_time
            for key in part.print_materials:
                try:
                    self._print_materials[key] += part.print_materials[key]
                except KeyError:
                    self._print_materials[key] = part.print_materials[key]

        # If everything above is fine, add part to list
        self._parts[part.base_name].update({part.cnd: part})

    @property
    def base_names(self):
        """Return base names in Build w/ 1 or more specimens"""
        base_names = []
        for base_name in self._parts:
            if len(self._parts[base_name]):
                base_names.append(base_name)
        return base_names

    @property
    def batch(self):
        """Return assigned batch"""
        return self._batch

    @property
    def machine(self):
        """Return assigned machine"""
        return self._machine

    @property
    def parts(self):
        """Returns a copied list containing all parts in build"""
        parts = []
        for base_name in self._parts:
            for cnd in self._parts[base_name]:
                parts.append(self._parts[base_name][cnd])
        return parts

    @property
    def print_materials(self):
        """Returns dictionary containing build's net use of materials"""
        return self._print_materials

    @property
    def print_time(self):
        """Return build's approximate print time"""
        return self._print_time


class BuildCollection(object):
    """A collection of builds"""

    def __init__(self, num_builds=1, build_kwargs={}):
        """Create a number of uniqely identified builds to common params

        @param num_builds Number of builds for collection to be formed with
        @param build_kwargs Keyword arguments to use for each build
        """
        self.builds = [
            Build('B-{}'.format(i), **build_kwargs) for i in range(num_builds)
        ]

        self.build_kwargs = build_kwargs
        self.num_builds = num_builds

    def assign_part(self, part):
        """Assign a part to one of the collection builds.

        If it cannot fit, spawn a new build

        @param part The Test tuple to add
        """
        part_assigned = False
        eligible_builds_lazy = self.filter_builds(
            batch=part.batch,
            machine=part.machine,
            materials=part.print_materials,
        )
        eligible_builds= self.filter_builds(
            batch=part.batch,
            machine=part.machine,
            base_name=part.base_name,
        )

        while not part_assigned:
            try:
                expected_build = random.choice(eligible_builds)
            except IndexError:
                # If we're empty, either move off of the strict list or spawn a
                # new build
                if eligible_builds_lazy is not None:
                    print('No good match, being lazy')
                    eligible_builds = eligible_builds_lazy
                    eligible_builds_lazy = None
                    continue
                else:
                    print('No match, new build!')
                    expected_build = self.spawn_build()
            try:
                expected_build.add_part(part)
                print('{} assigned to {}'.format(part.name, expected_build))
                part_assigned = True
            except RuntimeError as e:
                eligible_builds.remove(expected_build)
                print('{} failed - {}. Trying again'.format(
                    expected_build, e.args[0]))

    def assign_parts(self, parts):
        """Assign multiple parts to collection

        First sort parts by material in descending order - materials are
        prioritized based on 'max material' param in first build. Lower max is
        prioritized

        @param parts Iterable of Test tuples to add
        """
        max_material = {k: v for k,  v in sorted(
            self.builds[0].max_material.items(),
            key=lambda x: x[1],
            reverse=True
        )}

        for key in max_material:
            parts.sort(key=lambda x: x.print_materials[key], reverse=True)

        for part in parts:
            self.assign_part(part)

    def build_summary(self):
        """Returns a string representing each build w/ metadata"""
        retstr = []

        for build in self.builds:
            retstr.append('- {}:\t{} parts\t{}\t({})'.format(
                build.name,
                len(build.parts),
                build.print_materials,
                timedelta(seconds=build.print_time)
            ))

        return '\n'.join(retstr)

    def filter_builds(self, batch=None, machine=None, materials={}, base_name=None):
        """Filters build list based on desired parameters.

        Material content will not be checked if base name is specified due to
        complexity

        @param batch Desired batch to match
        @param machine Desired machine to match
        @param materials Dict containing desired remaining material, in cc
        @param base_name Base name of part

        @returns A filtered list of the desired builds
        """
        if batch is not None:
            builds = [build for build in self.builds
                      if build.batch == batch or build.batch is None]
        if machine is not None:
            builds = [build for build in builds
                      if build.machine == machine or build.machine is None]
        if base_name is not None:
            builds = [build for build in builds
                      if base_name in build.base_names]
        else:
            for key in materials:
                builds = [build for build in builds
                          if (build.max_material.get(key, 0)
                              - build.print_materials.get(key, 0))
                             >= materials[key]]

        return builds

    def spawn_build(self):
        """Add a new build to the collection"""
        self.builds.append(Build(
            'B-{}'.format(self.num_builds),
            **self.build_kwargs
        ))
        self.num_builds += 1

        return self.builds[-1]

    def to_csv(self, filename):
        """Save output to CSV

        @param filename Name of file to save results to
        """
        part_list = []
        for build in self.builds:
            part_list.append(','.join([
                '"{}"'.format(build),
                '"{}"'.format(repr(build)),
                BATCH_MAP[build.batch],
                MACHINE_MAP[build.machine],
                '"{}"'.format(str(build.print_time)),
                *['"{}"'.format(mat) for mat in {
                    k: v for k, v in sorted(build.print_materials.items())
                 }.values()],
                ]))

        with open(filename, 'w') as output_file:
            output_file.write('\n'.join(part_list))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Randomly assigns tests to builds'
    )

    parser.add_argument('test_matrix', help='File containing test matrix JSON')
    parser.add_argument('output', default='test-list.csv', nargs='?',
                        help='Name of file to store output CSV to')
    parser.add_argument('--num_builds', '-b', default=1, type=int,
                        help='Number of builds to start in collection')
    parser.add_argument('--seed', '-s', default=None, type=int,
                        help='Random seed')

    args = parser.parse_args()

    if args.seed is None:
        args.seed = random.randrange(2 ** 31 - 1)
    print('\nSeed is: {}'.format(args.seed))
    random.seed(args.seed)

    # Load matrix
    with open(args.test_matrix, 'r') as test_matrix_file:
        test_matrix = json.load(test_matrix_file)
    # Parse
    test_list = matrix_generator.matrix_to_list(test_matrix)
    # Assign to builds
    collection = BuildCollection(
        args.num_builds,
        build_kwargs={'max_material': {'OFA': 750, 'CFA': 45}}
    )
    collection.assign_parts(test_list)
    # Write out
    collection.to_csv(args.output)
    print('\nSummary of builds:')
    print(collection.build_summary())
    with open('build_summary.txt', 'w') as summary:
        summary.write(collection.build_summary())
