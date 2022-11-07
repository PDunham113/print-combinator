# print-randomizer

This selection of scripts takes a test matrix of printed parts, creates a sample
list, and organizes it into a series of builds.


## Sample list generation
Sample list generation creates a list of each possible permutation from a given
test matrix.

## Build organization
Parts are randomly assigned to builds using a PRNG, allowing a given "seed" to
repeatedly generate the same build list. When randomizing parts, the following
constraints are maintained:
-   Each build is kept below <X> cc of fiber
-   Each build is kept below <Y> cc of matrix material
-   ZX orientation parts are printed such that a build contains a set number of
    samples (ZX parts are printed as "tubes" and postprocessed, resulting in
    multiple samples per print)

At the beginning of the process, a minimum number of builds is set. For each
part, a list of eligible builds (builds that would meet the above criteria if
the part was added) is generated, and the part is assigned at random. This
process proceeds until no more parts remain.

If at any point, there is no build that can successfully contain a part, a new
build is created containing that part. Future parts will then have a chance to
be assigned to this newly-created build. To avoid this situation as much as
possible, the list of parts is sorted such that those requiring the most
material are assigned first. Fiber is considered higher priority than matrix
material.
