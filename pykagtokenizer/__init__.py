import pytjs
import sys
from pathlib import Path
import json
ScriptEngine = pytjs.tTJS()
ScriptEngineGlobal = ScriptEngine.GetGlobal()

with open(Path(__file__).parent.joinpath("KAGParser.tjs"), encoding="utf-8-sig") as f:
	ScriptEngine.ExecScript(f.read(), None, "KAGParser.tjs")
	
KAGParser = ScriptEngineGlobal.KAGParser

def todict(obj):
	is_array = ScriptEngine.EvalExpression("function(x){ return x instanceof 'Array';}")
	is_dictionary = ScriptEngine.EvalExpression("function(x){ return x instanceof 'Dictionary';}")
	if is_dictionary(obj):
		data = {}
		for k in obj:
			data[k] = todict(obj[k])
		return data
	elif is_array(obj):
		data = []
		for v in obj:
			data.append(todict(v))
		return data
	elif isinstance(obj, pytjs.iTJSDispatch2):
		return None
	else:
		return obj

def tokenize_scenario(instring, infilename="hoge.ks"):
	KAGParserInstance = KAGParser()
	KAGParserInstance.loadScenario(infilename, instring)
	return todict(KAGParserInstance.getParsedScenario())

if __name__ == '__main__':
	if len(sys.argv) >= 2:
		with open(sys.argv[1], encoding="utf-8-sig") as f:
			stru = tokenize_scenario(f.read(), sys.argv[1])
			if len(sys.argv) >= 3:
				with open(sys.argv[2], "w") as outfile:
					json.dump(stru, outfile)