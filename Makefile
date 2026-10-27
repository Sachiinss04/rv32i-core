# make test      : directed tests + 300 random programs, RTL vs Python ISS
# make mutation  : plant 16 RTL bugs, confirm the regression catches each
# make crosscheck: compare assembler output with GNU as (needs binutils)
test:
	python3 tools/run_tests.py 300
mutation:
	python3 tools/mutation_test.py
crosscheck:
	python3 tools/crosscheck_gnu.py
clean:
	rm -rf sim/build
