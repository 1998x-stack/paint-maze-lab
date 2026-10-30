.PHONY: run test bench
run:
	python3 server.py --host 127.0.0.1 --port 8765

test:
	python3 -m unittest discover -s tests -p 'test_*.py' -v
	npm test
	npm run check

bench:
	python3 benchmarks/run.py --samples 120 --width 4 --height 4 --seed 2026 --budget 40000 --output results/v2_benchmark_4x4.json
	python3 benchmarks/run.py --samples 80 --width 5 --height 5 --seed 2026 --budget 30000 --output results/v2_benchmark_5x5.json
