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
	def __str__(self):
		return self.__repr__()

class Utility:
	def __init__(self, headerLine, dataLines):
		# self.var = filter(None, re.split("[| ]+", headerLine))
		self.var = headerLine.split(' | ')[1].split(' ')
		self.ut = {}
		print dataLines
		for dataLine in dataLines:
			[valStr,signs] = dataLine.split(' ', 1)
			print signs
			keyBool = [(True if sign == '+' else False) for sign in signs.split(' ')]
			# keyBool = True if signs == '+' else False
			self.ut.update({tuple(keyBool): int(valStr)})
	
	@classmethod
	def fromLines(cls, headerLine, dataLines):
		var = filter(None, re.split("[| ]+", headerLine))

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
		# vars = self.unionVar(self.var, other.var)
		vars = list(set(self.var) | set(other.var))
		cpt = dict((self.event_values(e, vars), self.p(e) * other.p(e)) for e in self.all_events(vars, bn, {}))
		return Factor(vars, cpt)

	def sumOut(self, var, bn):
		vars = [X for X in self.var if X != var]
		cpt = dict((self.event_values(e, vars), sum(self.p(self.extend(e, var, val)) for val in [True, False])) for e in self.all_events(vars, bn, {}))
		return Factor(vars, cpt)

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
		"Yield every way of extending e with values for all vars."
		if not vars:
			yield e
		else:
			X, rest = vars[0], vars[1:]
			for e1 in self.all_events(rest, bn, e):
				for x in [True, False]:
					yield self.extend(e1, X, x)
	def p(self, e):
		"Look up my value tabulated for e."
		return self.cpt[self.event_values(e, self.var)]

	def extend(self, s, var, val):
		# extend({x: 1}, y, 2) = {y: 2, x: 1}
		s2 = s.copy()
		s2[var] = val
		return s2

	def event_values(self, event, vars):
		# """Return a tuple of the values of variables vars in event.
		# >>> event_values ({'A': 10, 'B': 9, 'C': 8}, ['C', 'A'])
		# (8, 10)
		# >>> event_values `((1, 2), ['C', 'A'])
		# (1, 2)
		# """
		if isinstance(event, tuple) and len(event) == len(vars):
			return event
		else:
			return tuple([event[var] for var in vars])

	# def unionVar(self, v1, v2):
	# 	v = v1 + v2
	# 	return v

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
		# allEvents = self.x + self.e if bool(self.e) else self.x
		# return for event in allEvents
	def getAllWithSigns(self):
		# for utility:
		# EU(Infiltration = + | LeakIdea = +) =>
		# Infiltration = +, LeakIdea = +
		xString = ', '.join([str(event.event) + ' = ' + '+' if event.outcome else '-' for event in self.x])
		eString = ', '.join([str(event.event) + ' = ' + '+' if event.outcome else '-' for event in self.e]) if bool(self.e) else ''
		return xString + (', ' + eString if bool(self.e) else '')

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
					print "this is a utility"
					while bool(line):
						# self.utility = Utility(,)
						if currentLineIsHeader:
							headerLine = line
							line = nextLine(f)
							currentLineIsHeader = False
						else:
							dataLines.append(line)
							line = nextLine(f)
					self.utility = Utility(headerLine, dataLines)
					print self.utility
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
		print '************ bn ****************'
		print self.bn
		print '********************************'

		for query in self.queryList:
			print query
			if query.queryType == 'P':
				result = self.eliminationAsk(query)
			elif query.queryType == 'EU':
				result = self.calculateEU(query)
			elif query.queryType == 'MEU':
				result = self.calculateMEU(query)
			self.writeToLog(result, query.queryType)
		self.exportTextFile("output.txt")

	def calculateEU(self, query):
		print ">>> calculate - EU"
		print query
		u = self.utility
		print u
		# calculate p vector
		pQueryEString = query.getAllWithSigns()
		pQueryXList = filter(lambda x: not x in query.getVariables(), u.getVariables())
		commonXList = filter(lambda x: x in query.getVariables(), u.getVariables())
		
		
		pQueryXStringList = self.getpQueryXStringList(pQueryXList)
		pVector = []
		for pQueryXString in pQueryXStringList:
			pQueryString = 'P(' + pQueryXString + ' | ' + pQueryEString + ')'
			print pQueryString
			pVector.append(self.eliminationAsk(Query(pQueryString)))
		print pVector

		# uQueryFixedXList
		# uQueryVariaXList
		# uQueryXListString = .uQueryXList

		uQueryXList = u.getVariables()
		for i,x in enumerate(u.getVariables()): # E B F G
			if x in commonXList: # B G
				uQueryXList[i] = query.getEventOutcome(x)
		uQueryKeys = self.getuQueryKeys(uQueryXList)
		print uQueryKeys
		# calculate u vector
		uVector = [u.getValue(key) for key in uQueryKeys]
		print 'uVector = ', uVector
		#
		return numpy.dot(pVector, uVector)
		# for tf in [True, False]:
		# 	sign = '+' if tf else '-'
		# 	for utilityVar in u.getVariables():
		# 		pQueryString = 'P(' + u.getVariables() + ' = ' + sign + ' | ' + query.getAllWithSigns() + ')'
		# 		p = self.eliminationAsk(Query(pQueryString))
		# 		print pQueryString + ' = ' + str(p)
		# 		utility = utility + u.cpt[(True, tf)] * p

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



	def getpQueryXStringList(self, pQueryXList):
		tfCombinationList = getTruthCombination(len(pQueryXList))
		pQueryXStringList = []
		for tfCombination in tfCombinationList:
			eventStringList = []
			for pQueryX, tf in zip(pQueryXList, tfCombination):
				sign = '+' if tf else '-'
				eventStringList.append(pQueryX + ' = ' + sign)
			pQueryXStringList.append(', '.join(eventStringList))
		return pQueryXStringList


	def calculateMEU(self, query):
		# print ">>> calculate - MEU"
		# print query
		return 0

	def eliminationAsk(self, query):
		X = query.getVariables()
		e = query.getEvidences()

		factors = self.bn[:] # deepcopy 
		allVar = list(set().union(*[f.getVariables() for f in factors]))

		for var in allVar: # var is a string
			if not var in e and not var in X:
				# print "var:\n" + var + '\n'
				# print "factors:\n " + str(factors)
				relevantFactors = filter(lambda f: var in f.getVariables(), factors)
				factors = [f for f in factors if f not in relevantFactors]
				# print "relevantFactors:\n " + str(relevantFactors)
				# print '*********'
				# print 
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
			text = result ###??
		self.log += str(text) + '\n'

	def exportTextFile(self, fileName):
		f = open(fileName, "w")
		f.write(self.log.rstrip("\r\n"))
		f.close()

def main(argv):
	ProbabilisticInferenceSystem('samples/sample02.txt').analyze()
	# if argv[1] == '-i':
	# 	pis = ProbabilisticInferenceSystem(argv[2])
	# 	pis.analyze()

if __name__ == "__main__": main(sys.argv)
