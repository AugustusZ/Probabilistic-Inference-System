#!/usr/bin/python
# Auth: Yankuan Zhang

import sys
import copy # to deep copy a dict: d2 = copy.deepcopy(d)
import re
import itertools
import numpy
from decimal import *

###############################################################################
# helper function definitions:
###############################################################################

def getTruthCombination(n):
	return list(itertools.product([True,False], repeat = n))

def isNumber(string):
	pattern = re.compile("^[0-9]*\.?[0-9]+$")
	return bool(pattern.match(string))

def nextLine(f):
	return f.readline().rstrip('\r\n').rstrip(' ')

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

	def getVariable(self):
		return self.event

	def __repr__(self):
		return self.event + (' = ' + ('+' if self.outcome else '-') if self.isDecided else '')

class Utility:
	def __init__(self, headerLine, dataLines):
		# self.var = filter(None, re.split("[| ]+", headerLine))
		self.var = headerLine.split(' | ')[1].split(' ')
		self.ut = {}
		for dataLine in dataLines:
			[valStr,signs] = dataLine.split(' ', 1)
			keyBool = [(True if sign == '+' else False) for sign in signs.split(' ')]
			self.ut.update({tuple(keyBool): int(valStr)})

	def getVariables(self):
		return self.var[:]
	def getValue(self, k):
		return self.ut[k]
	def __repr__(self):
		return ', '.join(self.var) + '\n\t' + '\n\t'.join(str(e) + ' : ' + str(self.ut[e]) for e in self.ut) + '\n\n'

class Factor:
	# http://stackoverflow.com/a/141777/5920930
	def __init__(self, var, cpt):
		self.var = var
		self.cpt = cpt

	@classmethod
	def fromData(cls, var, cpt):
		return cls(var, cpt)

	@classmethod
	def fromLines(cls, headerLine, dataLines):
		var = filter(None, re.split("[| ]+", headerLine))
		# print dataLines

		if dataLines[0] == 'decision':
			cpt = {(True,): 1, (False,): 1}
			return cls(var, cpt)
		else:
			cpt = {}
			entries = [cls.makeEntry(dataLine.split(' ', 1)) for dataLine in dataLines]
			map(cpt.update, entries)
			return cls(var, cpt)

	@classmethod
	def makeEntry(cls, ls):
		value = float(ls[0])
		if len(ls) == 1:
			return {(True,): value, (False,): 1 - value}
		else:
			originalKey = [(True if sign == '+' else False) for sign in ls[1].split(' ')]
			return {tuple([True] + originalKey) : value, tuple([False] + originalKey) : 1 - value}

	def pointwiseProduct(self, other, bn):
		varList = list(set(self.var) | set(other.var))
		cpt = dict((self.event_values(e, varList), self.p(e) * other.p(e)) for e in self.all_events(varList, bn, {}))
		return Factor(varList, cpt)

	def sumOut(self, var, bn):
		varList = [X for X in self.var if not X == var]
		cpt = dict((self.event_values(e, varList), sum(self.p(self.extend(e, var, val)) for val in [True, False])) for e in self.all_events(varList, bn, {}))
		return Factor(varList, cpt)

	def normalize(self, query):#occurrence
		# assert len(self.var) == 1
		vs = self.var
		e = query.getEvidencesEvents()
		x = query.getVariablesEvents()
		d = self.cpt
		eventList = vs[:]
		for i, var in enumerate(vs):
			if var in e:
				eventList[i] = e[var]
			else:
				eventList[i] = None
		keys = []
		for t in getTruthCombination(len(x)):
			E = numpy.array(eventList)
			E[[i for i in range(len(eventList)) if eventList[i] is None]] = list(t)
			keys.append(tuple(list(E)))
		
		eventList = vs[:]
		for i, var in enumerate(vs):
			if var in e:
				eventList[i] = e[var]
			else:
				eventList[i] = x[var]
		return d[tuple(eventList)] / sum([d[key] for key in keys])
		# return {self.var[0] : dict((k, v) for ((k,), v) in self.cpt.items())}

	def all_events(self, vars, bn, e):
		if bool(vars):
			X, rest = vars[0], vars[1:]
			for e1 in self.all_events(rest, bn, e):
				for x in [True, False]:
					yield self.extend(e1, X, x)
		else:
			yield e

	def p(self, e):
		return self.cpt[self.event_values(e, self.var)]

	def extend(self, s, var, val):
		# extend({x: 1}, y, 2) = {y: 2, x: 1}
		s2 = copy.deepcopy(s)
		s2[var] = val
		return s2

	def event_values(self, event, varList):
		# """Return a tuple of the values of variables varList in event.
		# >>> event_values ({'A': 10, 'B': 9, 'C': 8}, ['C', 'A'])
		# (8, 10)
		# >>> event_values `((1, 2), ['C', 'A'])
		# (1, 2)
		# """
		if isinstance(event, tuple) and len(event) == len(varList):
			return event
		else:
			return tuple([event[var] for var in varList])

	def getVariables(self):
		return self.var[:] # a list of string

	def __repr__(self):
		return ', '.join(self.var) + '\n\t' + '\n\t'.join(str(e) + ' : ' + str(self.cpt[e]) for e in self.cpt) + '\n\n'

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

	def getVariables(self):
		return [event.getVariable() for event in self.x]

	def getEvidences(self):
		return [event.getVariable() for event in self.e] if bool(self.e) else []
	def getEvidencesEvents(self):
		return {event.event : event.outcome for event in self.e} if bool(self.e) else {}
	def getVariablesEvents(self):
		return {event.event : event.outcome for event in self.x}

	def getEventOutcome(self, k):
		d = copy.deepcopy(self.getEvidencesEvents())
		d.update(self.getVariablesEvents())
		return d[k]

	def getEvidencesStringWithSign(self):
		return ', '.join([(ev.event + ' = ' + ( '+' if ev.outcome else '-') ) for ev in self.e]) if bool(self.e) else ''

	def getAllWithSigns(self):
		# for utility:
		# EU(Infiltration = + | LeakIdea = +) =>
		# Infiltration = +, LeakIdea = +

		xString = ', '.join([(ev.event + ' = ' + ( '+' if ev.outcome else '-') ) for ev in self.x])
		eString = self.getEvidencesStringWithSign()
		return xString + ((', ' + eString) if bool(self.e) else '')

	def getXSigns(self):
		# return a tuple of string
		return tuple(['+' if event.outcome else '-' for event in self.x])

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
		
		# print self.queryList
		self.bn = []
		# read factors
		while True:
			line = nextLine(f)
			if bool(line):
				headerLine = ""
				dataLines = []
				currentLineIsHeader = True
				if line[0] == 'u':
					while bool(line):
						if currentLineIsHeader:
							headerLine = line
							line = nextLine(f)
							currentLineIsHeader = False
						else:
							dataLines.append(line)
							line = nextLine(f)
					self.utility = Utility(headerLine, dataLines)
				else:
					while bool(line) and not '*' in line:
						if currentLineIsHeader:
							headerLine = line
							line = nextLine(f)
							currentLineIsHeader = False
						else:
							dataLines.append(line)
							line = nextLine(f)
					factor = Factor.fromLines(headerLine, dataLines)
					self.bn.append(factor)
			else:
				break
		f.close()

	def analyze(self):
		# print 
		for query in self.queryList:
			if query.queryType == 'P':
				result = self.eliminationAsk(query)
			elif query.queryType == 'EU':
				result = self.calculateEU(query)
			elif query.queryType == 'MEU':
				result = self.calculateMEU(query)
			self.writeToLog(result, query.queryType)
		self.exportTextFile("output.txt")

	def calculateEU(self, query):
		u = self.utility
		# calculate p vector
		pQueryEString = query.getAllWithSigns() 
		pQueryXList = filter(lambda x: not x in query.getVariables(), u.getVariables())
		
		if pQueryXList == []:
			# pVector = [1] * len(pQueryXList)
			return u.getValue(tuple(query.getEventOutcome(each) for each in u.getVariables()))

		commonXList = filter(lambda x: x in query.getVariables(), u.getVariables())

		pQueryXStringList = self.getQueryXStringList(pQueryXList)
		pVector = []
		for pQueryXString in pQueryXStringList:
			pQueryString = 'P(' + pQueryXString + ' | ' + pQueryEString + ')'
			pVector.append(self.eliminationAsk(Query(pQueryString)))

		uQueryXList = u.getVariables()
		for i,x in enumerate(u.getVariables()): # E B F G
			if x in commonXList: # B G
				uQueryXList[i] = query.getEventOutcome(x)
		uQueryKeys = self.getuQueryKeys(uQueryXList)
		# calculate u vector
		uVector = [u.getValue(key) for key in uQueryKeys]
		return numpy.dot(pVector, uVector)

	def getuQueryKeys(self, uQueryXList):
		tfInd = []
		for i, uQueryX in enumerate(uQueryXList):
			if type(uQueryX) is str:
				tfInd.append(i)
		tfCombinationList = getTruthCombination(len(tfInd))

		uQueryKeys = []
		for tfCombination in tfCombinationList:
			uQueryKey = uQueryXList[:]
			for i, tf in zip(tfInd, tfCombination):
				uQueryKey[i] = tf
			uQueryKeys.append(tuple(uQueryKey))
		return uQueryKeys

	def getQueryXStringList(self, QueryXList):
		tfCombinationList = getTruthCombination(len(QueryXList))
		QueryXStringList = []
		for tfCombination in tfCombinationList:
			eventStringList = []
			for QueryX, tf in zip(QueryXList, tfCombination):
				sign = '+' if tf else '-'
				eventStringList.append(QueryX + ' = ' + sign)
			QueryXStringList.append(', '.join(eventStringList))
		return QueryXStringList

	def calculateMEU(self, query):
		euQueryXStringList = self.getQueryXStringList(query.getVariables())
		euQueryEString = query.getEvidencesStringWithSign()

		allUtilities = {}
		for euQueryXString in euQueryXStringList:
			euQueryString = 'EU(' + euQueryXString +  ((' | ' + euQueryEString) if query.isConditional else '') + ')'
			euQuery = Query(euQueryString)
			allUtilities.update({euQuery.getXSigns() : self.calculateEU(euQuery)})
		meuKey = max(allUtilities.iterkeys(), key=lambda k: allUtilities[k])
		meuVal = allUtilities[meuKey]
		return meuKey, meuVal

	def eliminationAsk(self, query):
		X = query.getVariables()
		e = query.getEvidences()

		factors = self.bn[:] # deepcopy 
		allVar = list(set().union(*[f.getVariables() for f in factors]))

		for var in allVar: # var is a string
			if not var in e and not var in X:
				relevantFactors = filter(lambda f: var in f.getVariables(), factors)
				factors = [f for f in factors if f not in relevantFactors]
				factors.append(self.sumOut(var, self.pointwiseProduct(relevantFactors)))
		return self.pointwiseProduct(factors).normalize(query)

	def sumOut(self, var, factor):
		r = factor.sumOut(var, self.bn)
		# print "sumOut: " + str(r)
		return r

	def pointwiseProduct(self, factors):
		r = reduce(lambda f, g: f.pointwiseProduct(g, self.bn), factors)
		# print "ptwPdt " + str(r)
		return r

	def writeToLog(self, result, task):
		if task == 'P':
			text =  Decimal(result).quantize(Decimal('.01'))
		elif task == 'EU':
			text = int(round(result))
		elif task == 'MEU':
			# result = (TUPLE, INT)
			keyStr = ' '.join(result[0])
			valStr = str(int(round(result[1])))
			text = keyStr + ' ' + valStr
		self.log += str(text) + '\n'

	def exportTextFile(self, fileName):
		f = open(fileName, "w")
		f.write(self.log.rstrip("\r\n"))
		f.close()

def main(argv):
	# ProbabilisticInferenceSystem('samples/sample03.txt').analyze()
	if argv[1] == '-i':
		pis = ProbabilisticInferenceSystem(argv[2])
		pis.analyze()

if __name__ == "__main__": main(sys.argv)
