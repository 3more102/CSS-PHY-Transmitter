.PHONY: reference rtl lint verify all clean
reference:
	./scripts/run_reference_tests.sh
rtl:
	./scripts/run_rtl_tests.sh
lint:
	./scripts/run_lint.sh
verify:
	python3 scripts/run_verification.py
all: verify
clean:
	rm -rf results/sim reports/vivado results/*.dcp
