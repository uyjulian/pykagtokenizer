# pykagtokenizer

KAG tokenizer using Python.

# Usage

From command line to tokenize `.ks` to `.json`
```bash
python3 -m pykagtokenizer infile.ks outfile.json
```

Usage from Python script:
```py
import pykagtokenizer
structure = pykagtokenizer.tokenize_scenario("hoge[l][r]")
```

# License

MIT.
