
import re
import copy

##---------------------------------------------------------------------------
## KAG Parser Utility Class
##---------------------------------------------------------------------------

##---------------------------------------------------------------------------
## KAG System (Kirikiri Adventure Game System) is an application script for
## TVP(Kirikiri), providing core system for Adventure Game/Visual Novel.
## KAG has a simple tag-based mark-up language ("scenario file").
## Version under 2.x of KAG is slow since the parser is written in TJS1.
## KAG 3.x uses TVP's internal KAG parser written in C++ in this unit, will
## acquire speed in compensation for ability of customizing.
##---------------------------------------------------------------------------

TVPKAGNoLine = "Attempt to load scenario file %1 is empty"
TVPKAGCannotOmmitFirstLabelName = "The first label name of the scenario file cannot be omitted"
TVPInternalError = "Internal Error: at %1 line %2"
TVPKAGMalformedSaveData = "Bookmark data is abnormal. Data may be corrupted"
TVPKAGLabelNotFound = "Label %s not found in scenario file %s"
TVPKAGInlineScriptNotEnd = "[endscript] or @endscript not found"
TVPKAGSyntaxError = "Tag syntax error. Check for \'[\' and \']\' balance, \" and \" balance, missing spaces, extra line breaks, missing required attributes, etc."
TVPKAGSpecifyKAGParser = "Please specify an object of KAGParser class"

##---------------------------------------------------------------------------
## tTVPScenarioCacheItem : Scenario Cache Item
##---------------------------------------------------------------------------

class internal_KAGParser_ScenarioCacheItem:
	def __init__(self, name, isstring):
		self.lines = None
		self.lineCount = 0
		self.labelCache = {} # Label cache
		self.labelAliases = {}
		self.labelCached = False # whether the label is cached
		self.loadScenario(name, isstring)

	## load file or string to buffer
	def loadScenario(self, name, isstring):
		if type(name) is list:
			self.lines = name
		elif type(name) is str and isstring:
			## when onScenarioLoad returns string;
			## assumes the string is scenario
			self.lines = name.split("\n")
		elif type(name) is str:
			## else load from file
			self.lines = []
			with open(name) as f:
				for line in f.lines():
					self.lines.append(line)
		else:
			raise Exception("Name not Array or String!")
		## pass1: count lines
		## pass2: split lines
		for i in range(len(self.lines)):
			self.lines[i] = self.lines[i].lstrip("\t") ## skip leading tabs

		## tab-only last line will not be counted in pass2, thus makes
		## pass2 counted lines are lesser than pass1 lines.

		self.ensureLabelCache()

	def ensureLabelCache(self):
		## construct label cache
		if self.labelCached == False:
			## make label cache
			prevlabel = ""
			for i in range(len(self.lines)):
				line = self.lines[i]
				if len(line) >= 2 and line[0] == "*":
					## page name found
					label = line[:line.find("|")]
					if len(label) == 1:
						if len(prevlabel) == 0:
							raise Exception(TVPKAGCannotOmmitFirstLabelName)
						label = prevlabel

					prevlabel = label

					if label in self.labelCache:
						## previous label name found (duplicated label)
						self.labelCache[label][1] += 1
						label = ("%s:%s") % (label, i)

					self.labelCache[label] = [i, 1]
					self.labelAliases[i] = label
			self.labelCached = True

	def getLabelAliasFromLine(self, line):
		return self.labelAliases[line]

	def getLines(self):
		return self.lines

	def getLineCount(self):
		return len(self.lines)

	def getLabelCache(self):
		return self.labelCache

##---------------------------------------------------------------------------
## tTVPScenarioCache
##---------------------------------------------------------------------------
__internal_KAGParser_scenarios = {}

def internal_KAGParser_getScenario(storagename, isstring):
	## compact interface initialization
	if isstring:
		## we do not cache when the string is passed as a scenario
		return internal_KAGParser_ScenarioCacheItem(storagename, isstring)

	if not (storagename in __internal_KAGParser_scenarios):
		__internal_KAGParser_scenarios[storagename] = internal_KAGParser_ScenarioCacheItem(storagename, isstring)
	return __internal_KAGParser_scenarios[storagename]

##---------------------------------------------------------------------------
## tTJSNI_KAGParser : KAGParser TJS native instance
##---------------------------------------------------------------------------
## KAGParser is implemented as a TJS native class/object
class internal_KAGParser:
	def __init__(self):
		self.scenario = None # this is scenario object
		self.lines = None # is copied from Scenario
		self.lineCount = 0 # is copied from Scenario
		self.storageName = ""
		self.buffer = "" # not stored
		self.curLine = 0 # current processing line
		self.curPos = 0 # current processing position ( column )
		self.curLineStr = None # current line string; not stored
		self.curLabel = "" # Current Label
		self.curPage = "" # Current Page Name; not stored
		self.tagLine = 0 # line number of previous tag; not stored

		## retrieve DictClear method and DictObj object
		## retrieve clear method from dictclass
		# XXX: not used self.dicClear
		self.dicObj = {} # DictionaryObject

	def construct(self, tjs_obj):
		pass

	def finalize(self):
		## invalidate this object

		## release objects
		# XXX: not used self.dicClear
		self.dicObj = None

		self.clearBuffer()

	def loadScenario(self, name, buffer=None):
		## load scenario to buffer
		if name == self.storageName:
			## avoid re-loading
			self.rewind()
		else:
			self.clearBuffer()

			## fire onScenarioLoad
			ret = buffer
			if type(ret) is str:
				self.scenario = internal_KAGParser_getScenario(ret, True)
			else:
				self.scenario = internal_KAGParser_getScenario(name, False)
			self.lines = self.scenario.getLines()
			self.lineCount = self.scenario.getLineCount()

			self.rewind()

			self.storageName = name

	def getStorageName(self):
		return self.storageName

	## clear all states
	def clear(self):
		## clear all states
		## TVPClearScnearioCache() # also invalidates the scenario cache
		self.clearBuffer()

	## clear internal buffer
	def clearBuffer(self):
		## clear internal buffer
		if type(self.scenario) is internal_KAGParser_ScenarioCacheItem:
			self.scenario = None
			self.lines = None
			self.curLineStr = None
		self.storageName = ""

	## set current position to first
	def rewind(self):
		## set current position to first
		self.curLine = 0
		self.curPos = 0
		self.curLineStr = self.lines[0]

	def TVPIsWS(self, ch):
		## is white space ?
		return (ch == " " or ch == "\t")

	## skip comment or label and go to next line
	def skipCommentOrLabel(self):
		## skip comment or label, and go to next line.
		## fire OnScript event if [script] thru [endscript] ( or @script thru
		## @endscript ) is found.
		self.scenario.ensureLabelCache()
		self.curPos = 0
		if self.curLine >= self.lineCount:
			return None

		while self.curLine < self.lineCount:
			if self.lines == None:
				return None # in this loop, Lines can be NULL when onScript does so.

			p = self.lines[self.curLine]
			if len(p) >= 1 and p[0] == ";":
				if True:
					val = {}
					val["type"] = "comment"
					val["value"] = p[1:]
					self.curLine += 1
					return {"tagname": val}
				continue # comment

			if len(p) >= 1 and p[0] == "*":
				## label
				vl = p.find("|")
				pagename = None
				if vl == -1:
					self.curLabel = self.scenario.getLabelAliasFromLine(self.curLine)
					self.curPage = ""
					pagename = False
				else:
					self.curLabel = self.scenario.getLabelAliasFromLine(self.curLine)
					self.curPage = p[vl + 1:]
					pagename = True
				## fire onLabel callback event
				if True:
					val = {}
					val["type"] = "label"
					if pagename:
						val["pagename"] = self.curPage
					val["value"] = self.curLabel[1:]
					self.curLine += 1
					return {"tagname": val}
				continue

			if (p == "[iscript]" or p == "[iscript]\\") or (p == "@iscript"):
				## inline TJS script

				script = ""
				self.curLine += 1
				script_start = self.curLine

				while self.curLine < self.lineCount:
					p = self.lines[self.curLine]
					if ((p == "[endscript]" or p == "[endscript]\\")) or (p == "@endscript"):
						break
					if True:
						script += p
						script += "\r\n"
					self.curLine += 1

				if self.curLine == self.lineCount:
					raise Exception(TVPKAGInlineScriptNotEnd)

				## fire onScript callback event
				if True:
					val = {}
					val["type"] = "iscript"
					val["value"] = script
					self.curLine += 1
					return {"tagname": val}
				continue

			break

			self.curLine += 1

		if self.curLine >= self.lineCount:
			return None

		self.curLineStr = self.lines[self.curLine]

		return {}

	def kagStepNext(self, ldelim):
		if ldelim == "":
			self.curLine += 1
			self.curPos = 0
		else:
			self.curPos += 1

	def _getNextTag(self):
		## get next tag and return information dictionary object.
		## return NULL if the tag not found.
		## normal characters are interpreted as a "ch" tag.
		## CR code is interpreted as a "r" tag.
		## returned tag's line number is stored to TagLine.
		## tag paremeters are stored into return value.
		## tag name is also stored into return value, naemd "__tag".

		## pretty a nasty code.

		if self.curLine >= self.lineCount:
			return None
		if self.lines == None:
			return None

		while True:
			self.dicObj.clear()
			# del self.dicObj[:] # clear dictionary object

			if self.curLine >= self.lineCount:
				break # all of scenario was decoded

			tagstartpos = self.curPos

			if self.curPos == 0:
				commentorlabel = self.skipCommentOrLabel()
				if type(commentorlabel) is dict and len(commentorlabel) != 0:
					return commentorlabel

			ldelim = None # last delimiter

			if self.curPos == 0 and len(self.curLineStr) > 0 and self.curLineStr[0] == "@":
				## line command mode
				ldelim = "" # tag last delimiter is a null terminater
			else:
				if (
					(len(self.curLineStr) == self.curPos) or
					(self.curLineStr[self.curPos] != "[") or
					(
						len(self.curLineStr) != self.curPos and
						len(self.curLineStr) != self.curPos + 1 and
						self.curLineStr[self.curPos] == "[" and
						self.curLineStr[self.curPos + 1] == "["
					)
					):
					## normal character
					if len(self.curLineStr) == self.curPos:
						## line ended
						self.curLine += 1
						self.curPos = 0
						continue
					self.tagLine = self.curLine
					ch = self.curLineStr[self.curPos]

					if ch == "\t":
						self.curPos += 1
					elif ch != "\n":
						self.dicObj["tagname"] = "ch"
						self.dicObj["text"] = ch
					else:
						##  \n  ( reline )
						self.dicObj["tagname"] = "r"

					if self.curLineStr[self.curPos] == "[":
						self.curPos += 1
					self.curPos += 1

					if True:
						return self.dicObj
					continue

				ldelim = "]"

			## a tag
			self.tagLine = self.curLine
			tagstart = self.curPos

			self.curPos += 1
			if len(self.curLineStr) == self.curPos:
				raise Exception(TVPKAGSyntaxError)

			## tag name
			while len(self.curLineStr) != self.curPos and self.TVPIsWS(self.curLineStr[self.curPos]):
				self.curPos += 1

			if len(self.curLineStr) == self.curPos:
				raise Exception(TVPKAGSyntaxError)
			## XXX: verify offset
			tagnamestart = self.curPos
			while len(self.curLineStr) != self.curPos and (not self.TVPIsWS(self.curLineStr[self.curPos])) and self.curLineStr[self.curPos] != ldelim:
				self.curPos += 1

			if tagnamestart == self.curPos:
				raise Exception(TVPKAGSyntaxError)

			tagname = self.curLineStr[tagnamestart:self.curPos]
			tagname = tagname.lower()
			if True:
				self.dicObj["tagname"] = tagname

			## tag attributes
			while True:
				while len(self.curLineStr) != self.curPos and self.TVPIsWS(self.curLineStr[self.curPos]):
					self.curPos += 1
				if (ldelim == "" and len(self.curLineStr) == self.curPos) or self.curLineStr[self.curPos] == ldelim:
					## tag-specific processing
					if True:
						## not a control tag

						self.kagStepNext(ldelim)

						return self.dicObj

						break

					self.kagStepNext(ldelim)
					break

				if len(self.curLineStr) == self.curPos:
					raise Exception(TVPKAGSyntaxError)

				attribnamestart = self.curPos
				while len(self.curLineStr) != self.curPos and not self.TVPIsWS(self.curLineStr[self.curPos]) and self.curLineStr[self.curPos] != "=" and ((self.curLineStr[self.curPos] != ldelim) if (ldelim != "") else True):
					self.curPos += 1

				attribnameend = self.curPos

				attribname = self.curLineStr[attribnamestart:attribnameend]

				## =
				while len(self.curLineStr) != self.curPos and self.TVPIsWS(self.curLineStr[self.curPos]):
					self.curPos += 1

				entity = False
				value = ""

				if self.curLineStr[self.curPos] != "=":
					## arrtibute value omitted
					value = "true" # always true
				else:
					if len(self.curLineStr) == self.curPos:
						raise Exception(TVPKAGSyntaxError)
					self.curPos += 1
					if len(self.curLineStr) == self.curPos:
						raise Exception(TVPKAGSyntaxError)
					while len(self.curLineStr) != self.curPos and self.TVPIsWS(self.curLineStr[self.curPos]):
						self.curPos += 1
					if len(self.curLineStr) == self.curPos:
						raise Exception(TVPKAGSyntaxError)

					## attrib value
					vdelim = 0 # value delimiter

					if self.curLineStr[self.curPos] == "&":
						entity = True
						self.curPos += 1

					if self.curLineStr[self.curPos] == "\"" or self.curLineStr[self.curPos] == "'":
						vdelim = self.curLineStr[self.curPos]
						self.curPos += 1

					valuestart = self.curPos

					while len(self.curLineStr) != self.curPos and ((self.curLineStr[self.curPos] != vdelim) if (vdelim != 0) else (self.curLineStr[self.curPos] != ldelim and not self.TVPIsWS(self.curLineStr[self.curPos]))):
						if self.curLineStr[self.curPos] == "`":
							## escaped with '`'
							self.curPos += 1
							if len(self.curLineStr) == self.curPos:
								raise Exception(TVPKAGSyntaxError)
						self.curPos += 1

					if ldelim != "" and len(self.curLineStr) == self.curPos:
						raise Exception(TVPKAGSyntaxError)

					valueend = self.curPos

					if vdelim != 0:
						self.curPos += 1

					## unescape ` character of value
					value = self.curLineStr[valuestart:valueend]

					if valuestart != valueend:
						## value has at least one character
						value_pos = 0
						if value[value_pos] == "&":
							entity = True
							value_pos += 1
						newvalue = ""
						while len(value) != value_pos:
							if value[value_pos] == "`":
								value_pos += 1
								if len(value) == value_pos:
									break
							newvalue += value[value_pos]
							value_pos += 1
						value = newvalue

				## special attibute processing
				valueVariant = None
				if True:
					## process expression entity argument
					if entity:
						valueVariant = {}
						valueVariant["type"] = "entity"
						valueVariant["value"] = value
					else:
						valueVariant = value

				## store value into the dictionary object
				if attribname != "":
					self.dicObj[attribname] = valueVariant

		return None

	def getParsedScenario(self):
		res = {}
		last_line = self.curLine
		last_line_str = self.curLineStr
		cur_line_array = []
		all_lines_array = []
		char_array = []
		while res != None:
			res = self._getNextTag()
			if res != None and len(res) != 0:
				if self.curLine != last_line or self.curLineStr != last_line_str:
					if len(char_array) > 0:
						cur_line_array.append("".join(char_array))
						del char_array[:]
					last_line = self.curLine
					last_line_str = self.curLineStr
					all_lines_array.append(cur_line_array)
					cur_line_array = []
				rres = copy.deepcopy(res)
				if rres["tagname"] == "ch" and type(rres["text"]) is str and len(rres["text"]) == 1 and len(rres) == 2:
					char_array.append(rres["text"])
				elif len(char_array) > 0:
					cur_line_array.append("".join(char_array))
					del char_array[:]
					cur_line_array.append(rres)
				else:
					cur_line_array.append(rres)
		if len(char_array) > 0:
			cur_line_array.append("".join(char_array))
			del char_array[:]
		if len(cur_line_array) > 0:
			all_lines_array.append(cur_line_array)
		return all_lines_array

	def getCurLabel(self):
		return self.curLabel

	def getCurLine(self):
		return self.curLine

	def getCurPos(self):
		return self.curPos

	def getCurLineStr(self):
		return self.curLineStr

class KAGParser:
	def __init__(self):
		"""
		Building a KAGParser object

		Build an object of class KAGParser.
		specified kind.
		"""
		self.internal_KAGParser_instance = None
		self.internal_KAGParser_instance = internal_KAGParser()
		self.internal_KAGParser_instance.construct(self)

	def finalize(self):
		pass

	def loadScenario(self, name, buffer):
		"""
		Loading a scenario

		Loads the specified scenario storage and sets the scenario loading position to the beginning of the storage.

		Parameters
		----------
		name : str
			Specifies the scenario storage to load.
		"""
		return self.internal_KAGParser_instance.loadScenario(name, buffer)

	def getParsedScenario(self):
		"""
		Get parsed scenario

		Build an object of class KAGParser.

		Returns
		-------
		list
			Tag information.
		"""
		return self.internal_KAGParser_instance.getParsedScenario()

	def clear(self):
		"""
		Clear object

		Clears the state of the object.
		"""
		return self.internal_KAGParser_instance.clear()

	# curLine, curPos, curLineStr, curStorage, curLabel notimpl

















