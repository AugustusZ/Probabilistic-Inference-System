#!/usr/bin/python
# Auth: Yankuan Zhang

import sys
import copy # to deep copy a dict: d2 = copy.deepcopy(d)
import re
import itertools

###############################################################################
# helper function definitions:
###############################################################################

def getTruthCombination(n):
	return list(itertools.product([True,False], repeat = n))

def isNumber(string):
	pattern = re.compile("^[0-9]*\.?[0-9]+$")
	return bool(pattern.match(string))

def nextLine(f):
	return f.readline().rstrip('\r\n')

###############################################################################
# class definitions:
###############################################################################

class Event:
	def __init__(self, string):
		# the string looks like:
		# 		"NightDefense = +"
		# 		"Decision" (?)

		self.isDecided = '=' in string

		if self.isDecided:
			[self.event, outcome] = string.split(' = ')
			self.outcome = True if outcome is '+' else False
		else:
			self.event = string
			self.outcome = None

	def __repr__(self):
		return self.event + (' = ' + ('+' if self.outcome else '-') if self.isDecided else '')
	def __str__(self):
		return self.__repr__()

class Node():
	def __init__(self, headerLine, dataLines):
		self.variables = filter(None, re.split("[| ]+", headerLine))
		self.parseAndSaveCpt(dataLines)
		# self.setCompleteCpt()
		print 

	def parseAndSaveCpt(self, dataLines):
		self.cpt = {}
		entries = [self.makeEntry(dataLine.split(' ', 1)) for dataLine in dataLines]
		map(self.cpt.update, entries)
		print self.cpt

	def makeEntry(self, ls):
		value = float(ls[0])
		if len(ls) == 1:
			return {(True,): value, (False,): 1 - value}
		else:
			originalKey = [(True if sign == '+' else False) for sign in ls[1].split(' ')]
			return {tuple([True] + originalKey) : value, tuple([False] + originalKey) : 1 - value}

class Query:
	def __init__(self, string):
		# the string looks like:
		# 		"P(NightDefense = +, Infiltration = -)"
		# 		"P(Demoralize = + | LeakIdea = +, Infiltration = +)"
		[self.queryType, events] = string.strip(')').split('(')
		self.isConditional = '|' in events

		if self.isConditional:
			[x, e] = events.split(' | ')
			self.x = [Event(X) for X in x.split(', ')]
			self.e = [Event(E) for E in e.split(', ')]
		else:
			self.x = [Event(X) for X in events.split(', ')]
			self.e = None
	def __repr__(self):
		return self.queryType + '(' + ', '.join(str(X) for X in self.x) + (' | ' + ', '.join(str(E) for E in self.e) if self.isConditional else '') + ')'
	def __str__(self):
		return self.__repr__()

class ProbabilisticInferenceSystem:
	def __init__(self, fileName):
		f = open(fileName)
		self.log = ""
		self.queryList = []

		# read queries until hit asterisk row for the first time
		while True:
			line = nextLine(f)
			if not '*' in line:
				self.queryList.append(Query(line))
			else:
				break
		
		self.bayesianNetwork = []
		# read nodes
		while True:
			line = nextLine(f)
			if bool(line):
				nodeHeaderLine = ""
				nodeDataLines = []
				currentLineIsHeader = True
				while bool(line) and not '*' in line:
					if currentLineIsHeader:
						nodeHeaderLine = line
						currentLineIsHeader = False
						line = nextLine(f)
					else:
						nodeDataLines.append(line)
						line = nextLine(f)
				node = Node(nodeHeaderLine, nodeDataLines)
				self.bayesianNetwork.append(node)
			else:
				break

		f.close()

	# def writeToLog(self, keyword, goal = None):
	# 	goalString = ": " + str(goal.getUnderscoredVersion()) if not goal is None else ""
	# 	tempLogLine = keyword + goalString + "\r\n";
	# 	# MAGIC HERE, DON'T TOUCH!
	# 	# self.logCheck["True"] = "ASTRINGCOULDNEVERBELIKETHIS!"
	# 	# self.logCheck["False"] = "NSTRINGCOULDNEVERBELIKETHIS!"
	# 	if True:#not self.logCheck[keyword] == tempLogLine: 
	# 		if True:#not tempLogLine == self.stringBuffer:
	# 			self.log += tempLogLine
	# 			self.stringBuffer = tempLogLine
	# 			self.logCheck[keyword] = tempLogLine

	# def exportTextFile(self, fileName):
	# 	f = open(fileName, "w")
	# 	f.write(self.log.rstrip("\r\n"))
	# 	f.close()
	# 	# print("{} is exported.".format(fileName))

	def analyze(self):
		pass

def main(argv):
	pis = ProbabilisticInferenceSystem('samples/sample01.txt')
	pis.analyze()
	# if argv[1] == '-i':
	# 	ls = LogicSystem(argv[2])
	# 	result = ls.prove()
	# 	ls.exportTextFile("output.txt")

if __name__ == "__main__": main(sys.argv)
