.PHONY: reference rtl rtl-msim lint verify all clean
reference:
	./scripts/run_reference_tests.sh
rtl:
	python3 matlab/vector_generation/generate_vectors.py
	./scripts/run_rtl_tests.sh
rtl-msim:
	python3 matlab/vector_generation/generate_vectors.py
	python3 scripts/run_rtl_tests_msim.py
lint:
	./scripts/run_lint.sh
verify:
	python3 scripts/run_verification.py
all: verify
clean:
	rm -rf results/sim reports/vivado results/*.dcp
