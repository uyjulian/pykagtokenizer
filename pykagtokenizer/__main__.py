
import pykagtokenizer

if __name__ == '__main__':
	import sys
	import json
	if len(sys.argv) >= 2:
		with open(sys.argv[1], encoding="utf-8-sig") as f:
			stru = pykagtokenizer.tokenize_scenario(f.read(), sys.argv[1])
			if len(sys.argv) >= 3:
				with open(sys.argv[2], "w") as outfile:
					json.dump(stru, outfile)
