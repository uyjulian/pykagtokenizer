from .KAGParser import KAGParser

def tokenize_scenario(instring, infilename="hoge.ks"):
	KAGParserInstance = KAGParser()
	KAGParserInstance.loadScenario(infilename, instring)
	return KAGParserInstance.getParsedScenario()
