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

	def getVariable(self):
		return self.event

	def __repr__(self):
		return self.event + (' = ' + ('+' if self.outcome else '-') if self.isDecided else '')
	def __str__(self):
		return self.__repr__()

class Factor():
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
		vars = list(set(self.var) | set(other.var))
		cpt = dict((self.event_values(e, vars), self.p(e) * other.p(e)) for e in self.all_events(vars, bn, {}))
		return Factor(vars, cpt)

	def sumOut(self, var, bn):
		vars = [X for X in self.var if X != var]
		cpt = dict((self.event_values(e, vars), sum(self.p(self.extend(e, var, val)) for val in [True, False])) for e in self.all_events(vars, bn, {}))
		return Factor(vars, cpt)

	def normalize(self, occurrence):
		print " -- VAR: " + str(self.var)
		print " -- CPT: " + str(self.cpt)
		# assert len(self.var) == 1
		return {self.var[0] : dict((k, v) for ((k,), v) in self.cpt.items())}

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
		# """Copy the substitution s and extend it by setting var to val; return copy.
		# >>> extend({x: 1}, y, 2)
		# {y: 2, x: 1}
		# """
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

	def getVaribales(self):
		return [event.getVariable() for event in self.x]

	def getEvidences(self):
		return [event.getVariable() for event in self.e] if bool(self.e) else []

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
		
		self.bn = []
		# read factors
		while True:
			line = nextLine(f)
			if bool(line):
				factorHeaderLine = ""
				factorDataLines = []
				currentLineIsHeader = True
				while bool(line) and not '*' in line:
					if currentLineIsHeader:
						factorHeaderLine = line
						currentLineIsHeader = False
						line = nextLine(f)
					else:
						factorDataLines.append(line)
						line = nextLine(f)
				factor = Factor.fromLines(factorHeaderLine, factorDataLines)
				self.bn.append(factor)
			else:
				break

		f.close()

	def analyze(self):
		print self.bn
		print '********************************'
		print 
		for query in self.queryList:
			print query
			self.eliminationAsk(query.getVaribales(), query.getEvidences())

	def eliminationAsk(self, X, e):
		factors = self.bn[:] # deepcopy 
		allVar = list(set().union(*[f.getVariables() for f in factors]))

		for var in allVar: # var is a string
			if not var in e and not var in X:
				print "var:\n" + var + '\n'
				print "factors:\n " + str(factors)
				relevantFactors = filter(lambda f: var in f.getVariables(), factors)
				factors = [f for f in factors if f not in relevantFactors]
				print "relevantFactors:\n " + str(relevantFactors)
				print '*********'
				print 
				factors.append(self.sumOut(var, self.pointwiseProduct(relevantFactors)))
		print self.normalize(self.pointwiseProduct(factors))

	def sumOut(self, var, factor):
		r = factor.sumOut(var, self.bn)
		print "sumOut: " + str(r)
		return r

	def pointwiseProduct(self, factors):
		r = reduce(lambda f, g: f.pointwiseProduct(g, self.bn), factors)
		print "ptwPdt " + str(r)
		return r

	def normalize(self, factor):
		print "~~~~~~~"
		print factor

	def writeToLog(self, keyword, goal = None):
		pass

	def exportTextFile(self, fileName):
		f = open(fileName, "w")
		f.write(self.log.rstrip("\r\n"))
		f.close()

def main(argv):
	pis = ProbabilisticInferenceSystem('samples/sample01.txt')
	pis.analyze()
	# if argv[1] == '-i':
	# 	pis = ProbabilisticInferenceSystem(argv[2])
	# 	pis.analyze()
	# 	pis.exportTextFile("output.txt")

if __name__ == "__main__": main(sys.argv)
