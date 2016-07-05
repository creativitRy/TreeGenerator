# TreeGenerator
# by ctRy

import random
import math
from collections import namedtuple
from pymclevel import alphaMaterials
from pymclevel import alphaMaterials, MCSchematic, MCLevel, BoundingBox

displayName = "[[Land] Tree Generator"

inputs = [
	(("Tree Generator by ctRy", "label"),
	("generates procedural trees using algorithms by Drake7707", "label"),
	("Operation:",(
					"Create Tree",
					"Delete Tree",
					"Remove Decay-able Leaves",)),
	("General", "title"),),
	
	(("Trunk Max Life:", 50),
	("Trunk Material:", alphaMaterials.Wood),
	("Branch at End of Life:", True),   #if true, the chance to spawn branches increases at end of life
	("Trunk Age to Thickness Ratio:", 0.04),  #compared to age, how thick is the trunk?
	("Splitting Percentage: 1 in", 100),
	("Split Trunk Life Multiplier:", 0.5),  #when split, the new trunk starts with age * multiplier
	("Curving Percentage: 1 in", 10),
	("Curving Max Angle:", 30),  #from the current vector, the new vector has to be within this angle
	("Trunk", "title"),),
	
	(("Branching Percentage: 1 in", 8),
	("Branching Min Angle:", 30),
	("Branching Max Angle:", 50),  #from the up vector (+y), the new vector has to be within this angle
	("Branch Life Multiplier:", 0.75),  #the new branch starts with age * multiplier
	("Branch Material:", alphaMaterials.Wood),
	("Branch Age to Thickness Ratio:", 0.02),
	("Branch Curving Percentage: 1 in", 5),
	("Branch Curving Max Angle:", 15),
	("Branch", "title"),),
	
	(("Leaves Percentage: 1 in", 4),  #when inverse age is this percentage or below from max life, leaves spawn
	("Number of Leaves Spawned:", 3),  
	("Leaves Max Life:", 4),
	("Leaves Material:", alphaMaterials.Leaves),
	("Leaves Age to Thickness Ratio:", 0.5),
	("Leaves", "title"))
]

Vector = namedtuple('Vector', 'x, y, z')

def addVector(v1, v2):
	return Vector(v1.x + v2.x, v1.y + v2.y, v1.z + v2.z)

def scaleVector(v1, num):
	return Vector(v1.x * num, v1.y * num, v1.z * num)

#precondition: axisVec is normalized
def mirrorVector(vec, axisVec):
	return addVector(vec, scaleVector(axisVec, -2 * dotProduct(vec, axisVec) / vectorLengthSquared(axisVec)))

def vectorLengthSquared(vec):
	return vec.x ** 2 + vec.y ** 2 + vec.z ** 2
def vectorLength(vec):
	return math.sqrt(vectorLengthSquared(vec))

def normalizeVector(vec):
	length = vectorLength(vec)
	return Vector(vec.x / length, vec.y / length, vec.z / length)

def dotProduct(v1, v2):
	return v1.x * v2.x + v1.y * v2.y + v1.z * v2.z

def crossProduct(v1, v2):
	return vectorLength(v1) * vectorLength(v2)

#degrees
def angleBetween(v1, v2):
	return math.degrees(math.acos(dotProduct(v1, v2)/ crossProduct(v1, v2)))

def randomUnitVector(): #http://math.stackexchange.com/questions/44689/how-to-find-a-random-axis-or-unit-vector-in-3d
	theta = random.uniform(0, 2 * math.pi)
	z = random.uniform(0, 2) - 1
	return Vector(math.sqrt(1 - z ** 2) * math.cos(theta), math.sqrt(1 - z ** 2) * math.sin(theta), z)

#generate random unit vectors until given angle is achieved
def randomVectorWithinAngle(vec1, angleMin, angleMax):
	while True:
		vec = randomUnitVector()
		if angleMin <= angleBetween(vec1, vec) <= angleMax:
			return vec

Cell = namedtuple('Cell', 'type, age, position, velocity')  #type = 0 is trunk 1 is branch 2 is leaves.  #vel is normalized
stack = []

tLife = 0
tBlock = None
tBranchMore = True
tThicknessRatio = 0.0
tSplit = 0
tSplitMult = 0.0
tCurve = 0
tCurveAngle = 0

bPercent = 0
bMinAngle = 0
bMaxAngle = 0
bLifeMult = 0.0
bBlock = None
bThicknessRatio = 0.0
bCurve = 0
bCurveAngle = 0

lPercent = 0
lNum = 0
lLife = 0
lBlock = None
lThicknessRatio = 0.0

def perform(level, box, options):
	global tLife, tBlock, tBranchMore, tThicknessRatio, tSplit, tSplitMult, tCurve, tCurveAngle
	tLife = options["Trunk Max Life:"]
	tBlock = options["Trunk Material:"]
	tBranchMore = options["Branch at End of Life:"]
	tThicknessRatio = options["Trunk Age to Thickness Ratio:"]
	tSplit = options["Splitting Percentage: 1 in"]
	tSplitMult = options["Split Trunk Life Multiplier:"]
	tCurve = options["Curving Percentage: 1 in"]
	tCurveAngle = options["Curving Max Angle:"]
	
	global bPercent, bMinAngle, bMaxAngle, bLifeMult, bBlock, bThicknessRatio, bCurve, bCurveAngle
	bPercent = options["Branching Percentage: 1 in"]
	bMinAngle = options["Branching Min Angle:"]
	bMaxAngle = options["Branching Max Angle:"]
	bLifeMult = options["Branch Life Multiplier:"]
	bBlock = options["Branch Material:"]
	bThicknessRatio = options["Branch Age to Thickness Ratio:"]
	bCurve = options["Branch Curving Percentage: 1 in"]
	bCurveAngle = options["Branch Curving Max Angle:"]
	
	global lPercent, lNum, lLife, lBlock, lThicknessRatio
	lPercent = options["Leaves Percentage: 1 in"]
	lNum = options["Number of Leaves Spawned:"]
	lLife = options["Leaves Max Life:"]
	lBlock = options["Leaves Material:"]
	lThicknessRatio = options["Leaves Age to Thickness Ratio:"]
	
	#=======================
	global stack
	if options["Operation:"] == "Create Tree":
		print("Creating Tree . . .")
		stack = [Cell(0, tLife, Vector(box.minx, box.miny, box.minz), Vector(0, 1, 0) )]
		while stack:  #while stack not empty
			cell = stack.pop(0)
			if cell.age <= 0:  #inverse age of 0 or below are removed from the stack
				continue
			
			drawCell(level, cell)
			
			if cell.type == 2 or (cell.type == 0 and cell.age == tLife):
				moveCell(cell)
				continue
			if cell.type == 0 and cell.age <= 2 and tBranchMore:
				moveCell(cell)
				branchCell(cell)
				continue
			
			if cell.type == 0 and tSplit != 0 and random.randrange(0, tSplit) <= 0:
				splitTrunk(cell)
				continue
			if cell.type == 0 and tCurve != 0 and random.randrange(0, tCurve) <= 0:
				curveCell(cell)
				continue
			if cell.type == 1 and bCurve != 0 and random.randrange(0, bCurve) <= 0:
				curveCell(cell)
				continue
			
			if cell.type != 2 and bPercent != 0 and random.randrange(0, bPercent) <= 0:
				branchCell(cell)
			if cell.type != 2 and lPercent != 0 and cell.age * lPercent <= tLife:
				for i in xrange(0, lNum):
					growLeaves(cell)
			
			#if not split or curved
			moveCell(cell)
		
	elif options["Operation:"] == "Delete Tree":
		print("Deleting Tree . . .")
		stack = [Vector(box.minx, box.miny, box.minz)]
		while stack:
			cell = stack.pop()
			
			for xx in xrange(cell.x - 1, cell.x + 2):  #add neighboring blocks (including diagonals)
				for yy in xrange(cell.y - 1, cell.y + 2):
					for zz in xrange(cell.z - 1, cell.z + 2):
						if xx == cell.x and yy == cell.y and zz == cell.z:
							continue
						if level.blockAt(xx, yy, zz) == tBlock.ID and level.blockDataAt(xx, yy, zz) == tBlock.blockData:
							stack.append(Vector(xx, yy, zz))
						elif level.blockAt(xx, yy, zz) == bBlock.ID and level.blockDataAt(xx, yy, zz) == bBlock.blockData:
							stack.append(Vector(xx, yy, zz))
						elif level.blockAt(xx, yy, zz) == lBlock.ID and level.blockDataAt(xx, yy, zz) == lBlock.blockData:
							stack.append(Vector(xx, yy, zz))
			
			level.setBlockAt(cell.x, cell.y, cell.z, 0)
			level.setBlockDataAt(cell.x, cell.y, cell.z, 0)
	
	else:
		print("Deleting Decay-able Leaves . . .")
		stack = [Vector(box.minx, box.miny, box.minz)]
		woodStack = set()
		unusedStack = set()
		
		print("Part 1/3 - Searching all logs touching leaves")
		while stack:
			cell = stack.pop()
			for xx in xrange(cell.x - 1, cell.x + 2):
				for yy in xrange(cell.y - 1, cell.y + 2):
					for zz in xrange(cell.z - 1, cell.z + 2):
						if xx == cell.x and yy == cell.y and zz == cell.z:
							continue
						p = Vector(xx, yy, zz)
						if p in woodStack or p in unusedStack:
							continue
						if level.blockAt(xx, yy, zz) in (17, 162):
							stack.append(p)
			
			try:
				for xx in xrange(cell.x - 1, cell.x + 2):
					for yy in xrange(cell.y - 1, cell.y + 2):
						for zz in xrange(cell.z - 1, cell.z + 2):
							if xx == cell.x and yy == cell.y and zz == cell.z:
								continue
							if (xx == cell.x and (yy == cell.y or zz == cell.z)) or (yy == cell.y and zz == cell.z):
								if level.blockAt(xx, yy, zz) in (18, 161):
									woodStack.add(cell)
									raise BreakIt
				unusedStack.add(cell)
			except BreakIt:
				pass
		unusedStack.clear()
		numWood = len(woodStack)
		print(str(numWood) + " edge logs detected")
		print("")
		
		print("Part 2/2 - Analyzing leaves")
		leavesDict = {}
		diagStack = set()
		i = 1
		for log in woodStack:
			print(str(i) + " / " + str(numWood))
			stack = [log]
			leavesDict[log] = 0
			while stack:
				cell = stack.pop()
				
				for xx in xrange(cell.x - 1, cell.x + 2):
					for yy in xrange(cell.y - 1, cell.y + 2):
						for zz in xrange(cell.z - 1, cell.z + 2):
							if xx == cell.x and yy == cell.y and zz == cell.z:
								continue
							p = Vector(xx, yy, zz)
							if (xx == cell.x and (yy == cell.y or zz == cell.z)) or (yy == cell.y and zz == cell.z):
								if level.blockAt(xx, yy, zz) in (18, 161):
									if p not in leavesDict:
										stack.append(p)
										leavesDict[p] = leavesDict[cell] + 1
									else:
										if leavesDict[p] > leavesDict[cell] + 1:
											stack.append(p)
											leavesDict[p] = leavesDict[cell] + 1
							else:
								if level.blockAt(xx, yy, zz) in (18, 161):
									diagStack.add(p)
			i += 1
		print("")
		
		print("Part 3/3 - Deleting decay-able leaves")
		for p in leavesDict:
			if leavesDict[p] > 4: #minecraft default
				level.setBlockAt(p.x, p.y, p.z, 0)
				level.setBlockDataAt(p.x, p.y, p.z, 0)
		for cell in diagStack:
			if cell not in leavesDict:
				level.setBlockAt(cell.x, cell.y, cell.z, 0)
				level.setBlockDataAt(cell.x, cell.y, cell.z, 0)
	
	level.markDirtyBox(box)
	print("Done! :D")

#https://www.youtube.com/watch?v=5raSJHSXYts
#https://www.youtube.com/watch?v=8K0OtrXaGFw
#http://drake7707.blogspot.com/2010/11/2d-tree-generation-algorithm.html

class BreakIt(Exception): pass

def moveCellWithVel(cell, vel, ageMult = 1.0):
	stack.append(Cell(cell.type, int(round(cell.age * ageMult)) - 1, addVector(cell.position, vel), vel))

def moveCell(cell):
	moveCellWithVel(cell, cell.velocity)

def branchCell(cell):
	print("branched")
	vel = randomVectorWithinAngle(Vector(0, 1, 0), bMinAngle, bMaxAngle)
	stack.append(Cell(1, int(round(cell.age * bLifeMult)) - 1, addVector(cell.position, vel), normalizeVector(vel)))

def curveCell(cell):
	print("curved")
	max = 0
	if cell.type == 0:
		max = tCurveAngle
	elif cell.type == 1:
		max = bCurveAngle
	else:
		max = 2 #lCurveAngle
	
	vel = randomVectorWithinAngle(cell.velocity, 1, max)
	moveCellWithVel(cell, normalizeVector(vel))

def splitTrunk(cell):
	print("split")
	
	vel = randomVectorWithinAngle(Vector(0, 1, 0), 10, 90)
	moveCellWithVel(cell, vel, tSplitMult)
	
	moveCellWithVel(cell, normalizeVector(Vector(vel.x * -1, vel.y, vel.z * -1)), tSplitMult)

def growLeaves(cell):
	vel = randomVectorWithinAngle(cell.velocity, 10, 170)
	stack.append(Cell(2, lLife, addVector(cell.position, vel), vel))
	


def drawCell(level, cell):
	if cell.type == 0:
		drawSphere(level, cell.position, cell.age * tThicknessRatio, tBlock)
	elif cell.type == 1:
		drawSphere(level, cell.position, cell.age * bThicknessRatio, bBlock)
	else:
		drawSphere(level, cell.position, cell.age * lThicknessRatio, lBlock)

#Draws a hollow 3d sphere
def drawSphere(level, pos, dd, block):
	d = int(math.ceil(dd))
	r = d / 2
	
	#center coord
	xx = pos.x
	yy = pos.y
	zz = pos.z
	if d % 2 == 0:
		xx += 0.5
		yy += 0.5
		zz += 0.5
	
	for xxx in xrange(0, d):
		for yyy in xrange(0, d):
			for zzz in xrange(0, d):
				if int(math.sqrt((xxx - r) ** 2 + (yyy - r) ** 2 + (zzz - r) ** 2)) <= r:
					if level.blockAt(int(xxx - r + xx), int(yyy - r + yy), int(zzz - r + zz)) not in (tBlock.ID, bBlock.ID):
						level.setBlockAt(int(xxx - r + xx), int(yyy - r + yy), int(zzz - r + zz), block.ID)
						level.setBlockDataAt(int(xxx - r + xx), int(yyy - r + yy), int(zzz - r + zz), block.blockData)
