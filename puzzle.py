#!/usr/bin/env python

import archive
import lz77
import os.path
import struct
import sys
import time # FIXME: this is temporary

from ctypes import create_string_buffer
from PyQt5 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt


try:
    import nsmblib
    HaveNSMBLib = True
except ImportError:
    HaveNSMBLib = False


########################################################
# To Do:
#
#   - Object Editor
#       - Moving objects around
#
#   - Make UI simpler for Pop
#   - Animated Tiles
#   - fix up conflicts with different types of parameters
#   - C speed saving
#   - quick settings for applying to mulitple slopes
#
########################################################


Tileset = None
HexFont = None

#############################################################################################
########################## Tileset Class and Tile/Object Subclasses #########################

class TilesetClass():
    """Contains Tileset data. Inits itself to a blank tileset.
    Methods: addTile, removeTile, addObject, removeObject, clear"""

    class Tile():
        def __init__(self, image, noalpha, bytelist):
            """Tile Constructor"""
                        
            self.image = image
            self.noalpha = noalpha
            self.byte0 = bytelist[0]
            self.byte1 = bytelist[1]
            self.byte2 = bytelist[2]
            self.byte3 = bytelist[3]
            self.byte4 = bytelist[4]
            self.byte5 = bytelist[5]
            self.byte6 = bytelist[6]
            self.byte7 = bytelist[7]


    class Object():
    
        def __init__(self, height, width, uslope, lslope, tilelist):
            """Tile Constructor"""
            
            self.height = height
            self.width = width
            
            self.upperslope = uslope
            self.lowerslope = lslope
            
            self.tiles = tilelist
                        

    def __init__(self):
        """Constructor"""
        
        self.tiles = []
        self.objects = []
        
        self.slot = 1


    def addTile(self, image, noalpha, bytelist = (0, 0, 0, 0, 0, 0, 0, 0)):
        """Adds an tile class to the tile list with the passed image or parameters"""

        self.tiles.append(self.Tile(image, noalpha, bytelist))
        

    def addObject(self, height = 1, width = 1,  uslope = [0, 0], lslope = [0, 0], tilelist = [[(0, 0, 0)]]):
        """Adds a new object"""
        
        global Tileset
        
        if tilelist == [[(0, 0, 0)]]:
            tilelist = [[(0, 0, Tileset.slot)]]
            
        self.objects.append(self.Object(height, width, uslope, lslope, tilelist))
        
        
    def removeObject(self, index):
        """Removes an Object by Index number. Don't use this much, because we want objects to preserve their ID."""
        
        self.objects.pop(index)
       
    
    def clear(self):
        """Clears the tileset for a new file"""
        
        self.tiles = []
        self.objects = []
        
        
    def clearObjects(self):
        """Clears the object data"""
        
        self.objects = []
        
        
    def clearCollisions(self):
        """Clears the collisions data"""
        
        for tile in self.tiles:
            tile.byte0 = 0
            tile.byte1 = 0
            tile.byte2 = 0
            tile.byte3 = 0
            tile.byte4 = 0
            tile.byte5 = 0
            tile.byte6 = 0
            tile.byte7 = 0


#############################################################################################
######################### Palette for painting behaviors to tiles ##########################


class paletteWidget(QtWidgets.QWidget):
    
    def __init__(self, window):
        super().__init__(window)

        # Hex code editor
        self.hexEditor = QtWidgets.QLineEdit()
        self.hexEditor.setFont(HexFont)
        self.hexEditor.setText('0000 0000 0000 0000')
        self.hexEditor.textChanged.connect(self.hexEditorEdited)

        # Core Types Radio Buttons and Tooltips
        self.coreType = QtWidgets.QGroupBox()
        self.coreType.setTitle('Core Type:')
        self.coreWidgets = []
        coreLayout = QtWidgets.QVBoxLayout()
        rowA = QtWidgets.QHBoxLayout()
        rowB = QtWidgets.QHBoxLayout()
        rowC = QtWidgets.QHBoxLayout()
        rowD = QtWidgets.QHBoxLayout()
        rowE = QtWidgets.QHBoxLayout()
        rowF = QtWidgets.QHBoxLayout()

        path = os.path.dirname(os.path.abspath(sys.argv[0])) + '/Icons/'
        
        self.coreTypes = [['Default', QtGui.QIcon(path + 'Core/Default.png'), 'The standard type for tiles.\n\nAny regular terrain or backgrounds\nshould be of this type. It\n has no collision properties.'], 
                     ['Slope', QtGui.QIcon(path + 'Core/Slope.png'), 'Defines a sloped tile.\n\nSloped tiles have sloped collisions,\nwhich Mario can slide on.'], 
                     ['Reverse Slope', QtGui.QIcon(path + 'Core/RSlope.png'), 'Defines an upside-down slope.\n\nSloped tiles have sloped collisions,\nwhich Mario can slide on.'], 
                     ['Partial Block', QtGui.QIcon(path + 'Partial/Full.png'), 'Used for blocks with partial collisions.\n\nVery useful for Mini-Mario secret\nareas, but also for providing a more\naccurate collision map for your tiles.'],
                     ['Coin', QtGui.QIcon(path + 'Core/Coin.png'), 'Creates a coin.\n\nCoins have no solid collision,\nand when touched will disappear\nand increment the coin counter.'], 
                     ['Explodable Block', QtGui.QIcon(path + 'Core/Explode.png'), 'Specifies blocks which can explode.\n\nThese blocks will shatter into componenent\npieces when hit by a bom-omb or meteor.\nThe pieces themselves may be hardcoded\nand must be included in the tileset.\nbehavior may be sporadic.'], 
                     ['Climable Grid', QtGui.QIcon(path + 'Core/Climb.png'), 'Creates terrain that can be climbed on.\n\nClimable terrain cannot be walked on.\nWhen Mario is overtop of a climable\ntile and the player presses up,\nMario will enter a climbing state.'], 
                     ['Spike', QtGui.QIcon(path + 'Core/Spike.png'), 'Creates spike tiless.\n\nSpike tiles will damage Mario one hit\nwhen they are touched.'], 
                     ['Pipe', QtGui.QIcon(path + 'Core/Pipe.png'), 'Denotes a pipe tile.\n\nPipe tiles are specified according to\nthe part of the pipe. It\'s important\nto specify the right parts or\nentrances will not function correctly.'], 
                     ['Rails', QtGui.QIcon(path + 'Core/Rails.png'), 'Used for all types of rails.\n\nRails are replaced in-game with\n3D models, so modifying these\ntiles with different graphics\nwill have no effect.'],
                     ['Conveyor Belt', QtGui.QIcon(path + 'Core/Conveyor.png'), 'Defines moving tiles.\n\nMoving tiles will move Mario in one\ndirection or another. Parameters are\nlargely unknown at this time.']]

        i = 0
        for item in range(len(self.coreTypes)):
            self.coreWidgets.append(QtWidgets.QRadioButton())
            if i == 0:
                self.coreWidgets[item].setText('Default')
            else:
                self.coreWidgets[item].setIcon(self.coreTypes[item][1])
            self.coreWidgets[item].setIconSize(QtCore.QSize(24, 24))
            self.coreWidgets[item].setToolTip(self.coreTypes[item][2])
            self.coreWidgets[item].clicked.connect(self.swapParams)
            if i < 1:
                rowA.addWidget(self.coreWidgets[item])
            elif i < 3:
                rowB.addWidget(self.coreWidgets[item])
            elif i < 5:
                rowC.addWidget(self.coreWidgets[item])
            elif i < 7:
                rowD.addWidget(self.coreWidgets[item])
            elif i < 9:
                rowE.addWidget(self.coreWidgets[item])
            else:
                rowF.addWidget(self.coreWidgets[item])
            i += 1

        coreLayout.addLayout(rowA)
        coreLayout.addLayout(rowB)
        coreLayout.addLayout(rowC)
        coreLayout.addLayout(rowD)
        coreLayout.addLayout(rowE)
        coreLayout.addLayout(rowF)
        self.coreType.setLayout(coreLayout)


        # Properties Buttons. I hope this works well!
        self.propertyGroup = QtWidgets.QGroupBox()
        self.propertyGroup.setTitle('Properties:')
        propertyLayout = QtWidgets.QVBoxLayout()
        self.propertyWidgets = []
        propertyList = [['Solid', QtGui.QIcon(path + 'Prop/Solid.png'), 'Tiles you can walk on.\n\nThe tiles will be a solid basic square\nthrough which Mario can not pass.'], 
                        ['Block', QtGui.QIcon(path + 'Prop/Break.png'), 'This denotes breakable tiles such\nas brick blocks and Q blocks. It is likely that these\nare subject to the same issues as\nexplodable blocks. They emit a coin\nwhen hit.'],            
                        ['Falling Block', QtGui.QIcon(path + 'Prop/Fall.png'), 'Sets the block to fall after a set period. The\nblock is sadly replaced with a donut lift model\nfor all animations.'], 
                        ['Ledge', QtGui.QIcon(path + 'Prop/Ledge.png'), 'A ledge tile with unique properties.\n\nLedges can be shimmied along or\nhung from, but not walked along\nas with normal terrain. Must have the\nledge terrain type set as well.']]
        
        for item in range(len(propertyList)):
            self.propertyWidgets.append(QtWidgets.QCheckBox(propertyList[item][0]))
            self.propertyWidgets[item].setIcon(propertyList[item][1])
            self.propertyWidgets[item].setIconSize(QtCore.QSize(24, 24))
            self.propertyWidgets[item].setToolTip(propertyList[item][2])
            propertyLayout.addWidget(self.propertyWidgets[item])
        

        self.PassThrough = QtWidgets.QRadioButton('Pass-Through')
        self.PassDown = QtWidgets.QRadioButton('Pass-Down')
        self.PassNone = QtWidgets.QRadioButton('No Passing')

        self.PassThrough.setIcon(QtGui.QIcon(path + 'Prop/Pup.png'))
        self.PassDown.setIcon(QtGui.QIcon(path + 'Prop/Pdown.png'))
        self.PassNone.setIcon(QtGui.QIcon(path + 'Prop/Pnone.png'))

        self.PassThrough.setIconSize(QtCore.QSize(24, 24))
        self.PassDown.setIconSize(QtCore.QSize(24, 24))
        self.PassNone.setIconSize(QtCore.QSize(24, 24))

        self.PassThrough.setToolTip('Allows Mario to jump through the bottom\nof the tile and land on the top.')
        self.PassDown.setToolTip('Allows Mario to fall through the tile but\n be able to jump up through it. Originally\nused for invisible Q blocks.')
        self.PassNone.setToolTip('Default setting')

        propertyLayout.addWidget(self.PassNone)
        propertyLayout.addWidget(self.PassThrough)
        propertyLayout.addWidget(self.PassDown)

        self.propertyGroup.setLayout(propertyLayout)



        # Terrain Type ComboBox
        self.terrainType = QtWidgets.QComboBox()
        self.terrainLabel = QtWidgets.QLabel('Terrain Type')
 
        self.terrainTypes = [['Default', QtGui.QIcon(path + 'Core/Default.png')],
                        ['Ice', QtGui.QIcon(path + 'Terrain/Ice.png')], 
                        ['Snow', QtGui.QIcon(path + 'Terrain/Snow.png')], 
                        ['Quicksand', QtGui.QIcon(path + 'Terrain/Quicksand.png')], 
                        ['Conveyor Belt Right', QtGui.QIcon(path + 'Core/Conveyor.png')], 
                        ['Conveyor Belt Left', QtGui.QIcon(path + 'Core/Conveyor.png')],
                        ['Horiz. Climbing Rope', QtGui.QIcon(path + 'Terrain/Rope.png')], 
                        ['Damage Tile', QtGui.QIcon(path + 'Terrain/Spike.png')], 
                        ['Ledge', QtGui.QIcon(path + 'Terrain/Ledge.png')], 
                        ['Ladder', QtGui.QIcon(path + 'Terrain/Ladder.png')], 
                        ['Staircase', QtGui.QIcon(path + 'Terrain/Stairs.png')], 
                        ['Carpet', QtGui.QIcon(path + 'Terrain/Carpet.png')], 
                        ['Dusty', QtGui.QIcon(path + 'Terrain/Dust.png')], 
                        ['Grass', QtGui.QIcon(path + 'Terrain/Grass.png')], 
                        ['Muffled', QtGui.QIcon(path + 'Unknown.png')], 
                        ['Beach Sand', QtGui.QIcon(path + 'Terrain/Sand.png')]]

        for item in range(len(self.terrainTypes)):
            self.terrainType.addItem(self.terrainTypes[item][1], self.terrainTypes[item][0])
            self.terrainType.setIconSize(QtCore.QSize(24, 24))
        self.terrainType.setToolTip('Set the various types of terrain.\n\n'
                                    
                                    '<b>Default:</b> \nTerrain with no paticular properties.\n\n'
                                    '<b>Ice:</b> \nWill be slippery.\n\n'
                                    '<b>Snow:</b> \nWill emit puffs of snow and snow noises.\n\n'
                                    '<b>Quicksand:</b> \nWill slowly swallow Mario as if\nin quicksand. No animation.'
                                    '<b>Conveyor Belt Right:</b> \nMario moves slowly rightwards.'
                                    '<b>Converyor Belt Left:</b> \nMario moves slowly leftwards.'
                                    '<b>Horiz. Rope:</b> \nMust be solid to function.\nMario will move hand-over-hand\nalong the rope.'
                                    '<b>Damage Tile:</b> \nTile causes damage like a spike.'
                                    '<b>Ledge:</b> \nMust have ledge property set as well.'
                                    '<b>Ladder:</b> \nActs as a ladder. Mario will face right\nor left as he climbs.'
                                    '<b>Staricase:</b> \nSliding is not allowed on slopes, and\nhas other characteristics of a staircase.'
                                    '<b>Carpet:</b> \nWill muffle footstep noises.'
                                    '<b>Dusty:</b> \nWill emit puffs of dust.'
                                    '<b>Muffled:</b> \nMostly muffles footstep noises.'
                                    '<b>Grass:</b> \nWill emit grass-like footstep noises.'
                                    '<b>Beach Sand:</b> \nWill create sand tufts around\nMario\'s feet.'
                                   )

        
        
        # Parameters ComboBox
        self.parameters = QtWidgets.QComboBox()
        self.parameterLabel = QtWidgets.QLabel('Parameters')
        self.parameters.addItem('None')

        
        GenericParams = [['None', QtGui.QIcon(path + 'Core/Default.png')],
                         ['Beanstalk Stop', QtGui.QIcon(path + '/Generic/Beanstopper.png')], 
                         ['Dash Coin', QtGui.QIcon(path + 'Generic/Outline.png')], 
                         ['Battle Coin', QtGui.QIcon(path + 'Generic/Outline.png')],
                         ['Red Block Outline A', QtGui.QIcon(path + 'Generic/RedBlock.png')], 
                         ['Red Block Outline B', QtGui.QIcon(path + 'Generic/RedBlock.png')], 
                         ['Cave Entrance Right', QtGui.QIcon(path + 'Generic/Cave-Right.png')], 
                         ['Cave Entrance Left', QtGui.QIcon(path + 'Generic/Cave-Left.png')], 
                         ['Unknown', QtGui.QIcon(path + 'Unknown.png')],
                         ['Unknown', QtGui.QIcon(path + 'Unknown.png')]]
        
        RailParams = [['None', QtGui.QIcon(path + 'Core/Default.png')],
                      ['Rail: Upslope', QtGui.QIcon(path + '')], 
                      ['Rail: Downslope', QtGui.QIcon(path + '')], 
                      ['Rail: 90 degree Corner Fill', QtGui.QIcon(path + '')], 
                      ['Rail: 90 degree Corner', QtGui.QIcon(path + '')], 
                      ['Rail: Horizontal Rail', QtGui.QIcon(path + '')], 
                      ['Rail: Vertical Rail', QtGui.QIcon(path + '')], 
                      ['Rail: Unknown', QtGui.QIcon(path + 'Unknown.png')], 
                      ['Rail: Gentle Upslope 2', QtGui.QIcon(path + '')], 
                      ['Rail: Gentle Upslope 1', QtGui.QIcon(path + '')], 
                      ['Rail: Gentle Downslope 2', QtGui.QIcon(path + '')], 
                      ['Rail: Gentle Downslope 1', QtGui.QIcon(path + '')], 
                      ['Rail: Steep Upslope 2', QtGui.QIcon(path + '')], 
                      ['Rail: Steep Upslope 1', QtGui.QIcon(path + '')], 
                      ['Rail: Steep Downslope 2', QtGui.QIcon(path + '')], 
                      ['Rail: Steep Downslope 1', QtGui.QIcon(path + '')], 
                      ['Rail: One Panel Circle', QtGui.QIcon(path + '')], 
                      ['Rail: 2x2 Circle Upper Right', QtGui.QIcon(path + '')], 
                      ['Rail: 2x2 Circle Upper Left', QtGui.QIcon(path + '')], 
                      ['Rail: 2x2 Circle Lower Right', QtGui.QIcon(path + '')], 
                      ['Rail: 2x2 Circle Lower Left', QtGui.QIcon(path + '')], 
                      ['Rail: 4x4 Circle Top Left Corner', QtGui.QIcon(path + '')], 
                      ['Rail: 4x4 Circle Top Left', QtGui.QIcon(path + '')], 
                      ['Rail: 4x4 Circle Top Right', QtGui.QIcon(path + '')], 
                      ['Rail: 4x4 Circle Top Right Corner', QtGui.QIcon(path + '')], 
                      ['Rail: 4x4 Circle Upper Left Side', QtGui.QIcon(path + '')], 
                      ['Rail: 4x4 Circle Upper Right Side', QtGui.QIcon(path + '')], 
                      ['Rail: 4x4 Circle Lower Left Side', QtGui.QIcon(path + '')], 
                      ['Rail: 4x4 Circle Lower Right Side', QtGui.QIcon(path + '')], 
                      ['Rail: 4x4 Circle Bottom Left Corner', QtGui.QIcon(path + '')], 
                      ['Rail: 4x4 Circle Bottom Left', QtGui.QIcon(path + '')], 
                      ['Rail: 4x4 Circle Bottom Right', QtGui.QIcon(path + '')], 
                      ['Rail: 4x4 Circle Bottom Right Corner', QtGui.QIcon(path + '')], 
                      ['Rail: Unknown', QtGui.QIcon(path + 'Unknown.png')], 
                      ['Rail: End Stop', QtGui.QIcon(path + '')]]
        
        ClimableGridParams = [['None', QtGui.QIcon(path + 'Core/Default.png')],
                             ['Free Move', QtGui.QIcon(path + 'Climb/Center.png')], 
                             ['Upper Left Corner', QtGui.QIcon(path + 'Climb/UpperLeft.png')], 
                             ['Top', QtGui.QIcon(path + 'Climb/Top.png')], 
                             ['Upper Right Corner', QtGui.QIcon(path + 'Climb/UpperRight.png')], 
                             ['Left Side', QtGui.QIcon(path + 'Climb/Left.png')], 
                             ['Center', QtGui.QIcon(path + 'Climb/Center.png')], 
                             ['Right Side', QtGui.QIcon(path + 'Climb/Right.png')], 
                             ['Lower Left Corner', QtGui.QIcon(path + 'Climb/LowerLeft.png')], 
                             ['Bottom', QtGui.QIcon(path + 'Climb/Bottom.png')], 
                             ['Lower Right Corner', QtGui.QIcon(path + 'Climb/LowerRight.png')]]
        
        
        CoinParams = [['Generic Coin', QtGui.QIcon(path + 'QBlock/Coin.png')],
                     ['Coin', QtGui.QIcon(path + 'Unknown.png')], 
                     ['Nothing', QtGui.QIcon(path + 'Unknown.png')],
                     ['Coin', QtGui.QIcon(path + 'Unknown.png')], 
                     ['Pow Block Coin', QtGui.QIcon(path + 'Coin/POW.png')]]
                 
        ExplodableBlockParams = [['None', QtGui.QIcon(path + 'Core/Default.png')],
                                ['Stone Block', QtGui.QIcon(path + 'Explode/Stone.png')], 
                                ['Wooden Block', QtGui.QIcon(path + 'Explode/Wooden.png')], 
                                ['Red Block', QtGui.QIcon(path + 'Explode/Red.png')], 
                                ['Unknown', QtGui.QIcon(path + 'Unknown.png')], 
                                ['Unknown', QtGui.QIcon(path + 'Unknown.png')], 
                                ['Unknown', QtGui.QIcon(path + 'Unknown.png')]]
        
        PipeParams = [['Vert. Top Entrance Left', QtGui.QIcon(path + 'Pipes/')], 
                      ['Vert. Top Entrance Right', QtGui.QIcon(path + '')], 
                      ['Vert. Bottom Entrance Left', QtGui.QIcon(path + '')], 
                      ['Vert. Bottom Entrance Right', QtGui.QIcon(path + '')], 
                      ['Vert. Center Left', QtGui.QIcon(path + '')], 
                      ['Vert. Center Right', QtGui.QIcon(path + '')], 
                      ['Vert. On Top Junction Left', QtGui.QIcon(path + '')], 
                      ['Vert. On Top Junction Right', QtGui.QIcon(path + '')], 
                      ['Horiz. Left Entrance Top', QtGui.QIcon(path + '')], 
                      ['Horiz. Left Entrance Bottom', QtGui.QIcon(path + '')], 
                      ['Horiz. Right Entrance Top', QtGui.QIcon(path + '')], 
                      ['Horiz. Right Entrance Bottom', QtGui.QIcon(path + '')], 
                      ['Horiz. Center Left', QtGui.QIcon(path + '')], 
                      ['Horiz. Center Right', QtGui.QIcon(path + '')], 
                      ['Horiz. On Top Junction Top', QtGui.QIcon(path + '')], 
                      ['Horiz. On Top Junction Bottom', QtGui.QIcon(path + '')], 
                      ['Vert. Mini Pipe Top', QtGui.QIcon(path + '')], 
                      ['Unknown', QtGui.QIcon(path + 'Unknown.png')], 
                      ['Vert. Mini Pipe Bottom', QtGui.QIcon(path + '')], 
                      ['Unknown', QtGui.QIcon(path + 'Unknown.png')], 
                      ['Unknown', QtGui.QIcon(path + 'Unknown.png')], 
                      ['Unknown', QtGui.QIcon(path + 'Unknown.png')], 
                      ['Vert. On Top Mini-Junction', QtGui.QIcon(path + '')], 
                      ['Unknown', QtGui.QIcon(path + 'Unknown.png')], 
                      ['Horiz. Mini Pipe Left', QtGui.QIcon(path + '')], 
                      ['Unknown', QtGui.QIcon(path + 'Unknown.png')], 
                      ['Horiz. Mini Pipe Right', QtGui.QIcon(path + '')], 
                      ['Unknown', QtGui.QIcon(path + 'Unknown.png')], 
                      ['Vert. Mini Pipe Center', QtGui.QIcon(path + '')], 
                      ['Horiz. Mini Pipe Center', QtGui.QIcon(path + '')], 
                      ['Horiz. On Top Mini-Junction', QtGui.QIcon(path + '')], 
                      ['Block Covered Corner', QtGui.QIcon(path + '')]]
                                       
        PartialBlockParams = [['None', QtGui.QIcon(path + 'Core/Default.png')],
                              ['Upper Left', QtGui.QIcon(path + 'Partial/UpLeft.png')], 
                              ['Upper Right', QtGui.QIcon(path + 'Partial/UpRight.png')], 
                              ['Top Half', QtGui.QIcon(path + 'Partial/TopHalf.png')], 
                              ['Lower Left', QtGui.QIcon(path + 'Partial/LowLeft.png')], 
                              ['Left Half', QtGui.QIcon(path + 'Partial/LeftHalf.png')], 
                              ['Diagonal Downwards', QtGui.QIcon(path + 'Partial/DiagDn.png')], 
                              ['Upper Left 3/4', QtGui.QIcon(path + 'Partial/UpLeft3-4.png')], 
                              ['Lower Right', QtGui.QIcon(path + 'Partial/LowRight.png')], 
                              ['Diagonal Downwards', QtGui.QIcon(path + 'Partial/DiagDn.png')], 
                              ['Right Half', QtGui.QIcon(path + 'Partial/RightHalf.png')], 
                              ['Upper Right 3/4', QtGui.QIcon(path + 'Partial/UpRig3-4.png')], 
                              ['Lower Half', QtGui.QIcon(path + 'Partial/LowHalf.png')], 
                              ['Lower Left 3/4', QtGui.QIcon(path + 'Partial/LowLeft3-4.png')], 
                              ['Lower Right 3/4', QtGui.QIcon(path + 'Partial/LowRight3-4.png')], 
                              ['Full Brick', QtGui.QIcon(path + 'Partial/Full.png')]]
        
        SlopeParams = [['Steep Upslope', QtGui.QIcon(path + 'Slope/steepslopeleft.png')], 
                       ['Steep Downslope', QtGui.QIcon(path + 'Slope/steepsloperight.png')], 
                       ['Upslope 1', QtGui.QIcon(path + 'Slope/slopeleft.png')], 
                       ['Upslope 2', QtGui.QIcon(path + 'Slope/slope3left.png')], 
                       ['Downslope 1', QtGui.QIcon(path + 'Slope/slope3right.png')], 
                       ['Downslope 2', QtGui.QIcon(path + 'Slope/sloperight.png')], 
                       ['Steep Upslope 1', QtGui.QIcon(path + 'Slope/vsteepup1.png')], 
                       ['Steep Upslope 2', QtGui.QIcon(path + 'Slope/vsteepup2.png')], 
                       ['Steep Downslope 1', QtGui.QIcon(path + 'Slope/vsteepdown1.png')], 
                       ['Steep Downslope 2', QtGui.QIcon(path + 'Slope/vsteepdown2.png')], 
                       ['Slope Edge (solid)', QtGui.QIcon(path + 'Slope/edge.png')], 
                       ['Gentle Upslope 1', QtGui.QIcon(path + 'Slope/gentleupslope1.png')], 
                       ['Gentle Upslope 2', QtGui.QIcon(path + 'Slope/gentleupslope2.png')], 
                       ['Gentle Upslope 3', QtGui.QIcon(path + 'Slope/gentleupslope3.png')], 
                       ['Gentle Upslope 4', QtGui.QIcon(path + 'Slope/gentleupslope4.png')], 
                       ['Gentle Downslope 1', QtGui.QIcon(path + 'Slope/gentledownslope1.png')], 
                       ['Gentle Downslope 2', QtGui.QIcon(path + 'Slope/gentledownslope2.png')], 
                       ['Gentle Downslope 3', QtGui.QIcon(path + 'Slope/gentledownslope3.png')], 
                       ['Gentle Downslope 4', QtGui.QIcon(path + 'Slope/gentledownslope4.png')]]
                       
        ReverseSlopeParams = [['Steep Downslope', QtGui.QIcon(path + 'Slope/Rsteepslopeleft.png')], 
                              ['Steep Upslope', QtGui.QIcon(path + 'Slope/Rsteepsloperight.png')], 
                              ['Downslope 1', QtGui.QIcon(path + 'Slope/Rslopeleft.png')], 
                              ['Downslope 2', QtGui.QIcon(path + 'Slope/Rslope3left.png')], 
                              ['Upslope 1', QtGui.QIcon(path + 'Slope/Rslope3right.png')], 
                              ['Upslope 2', QtGui.QIcon(path + 'Slope/Rsloperight.png')], 
                              ['Steep Downslope 1', QtGui.QIcon(path + 'Slope/Rvsteepdown1.png')], 
                              ['Steep Downslope 2', QtGui.QIcon(path + 'Slope/Rvsteepdown2.png')], 
                              ['Steep Upslope 1', QtGui.QIcon(path + 'Slope/Rvsteepup1.png')], 
                              ['Steep Upslope 2', QtGui.QIcon(path + 'Slope/Rvsteepup2.png')], 
                              ['Slope Edge (solid)', QtGui.QIcon(path + 'Slope/edge.png')], 
                              ['Gentle Downslope 1', QtGui.QIcon(path + 'Slope/Rgentledownslope1.png')], 
                              ['Gentle Downslope 2', QtGui.QIcon(path + 'Slope/Rgentledownslope2.png')], 
                              ['Gentle Downslope 3', QtGui.QIcon(path + 'Slope/Rgentledownslope3.png')], 
                              ['Gentle Downslope 4', QtGui.QIcon(path + 'Slope/Rgentledownslope4.png')], 
                              ['Gentle Upslope 1', QtGui.QIcon(path + 'Slope/Rgentleupslope1.png')], 
                              ['Gentle Upslope 2', QtGui.QIcon(path + 'Slope/Rgentleupslope2.png')], 
                              ['Gentle Upslope 3', QtGui.QIcon(path + 'Slope/Rgentleupslope3.png')], 
                              ['Gentle Upslope 4', QtGui.QIcon(path + 'Slope/Rgentleupslope4.png')]]
        
        SpikeParams = [['Double Left Spikes', QtGui.QIcon(path + 'Spike/Left.png')], 
                       ['Double Right Spikes', QtGui.QIcon(path + 'Spike/Right.png')], 
                       ['Double Upwards Spikes', QtGui.QIcon(path + 'Spike/Up.png')], 
                       ['Double Downwards Spikes', QtGui.QIcon(path + 'Spike/Down.png')], 
                       ['Long Spike Down 1', QtGui.QIcon(path + 'Spike/LongDown1.png')], 
                       ['Long Spike Down 2', QtGui.QIcon(path + 'Spike/LongDown2.png')], 
                       ['Single Downwards Spike', QtGui.QIcon(path + 'Spike/SingDown.png')], 
                       ['Spike Block', QtGui.QIcon(path + 'Unknown.png')]]
        
        ConveyorBeltParams = [['Slow', QtGui.QIcon(path + 'Unknown.png')], 
                              ['Fast', QtGui.QIcon(path + 'Unknown.png')]]
        
        
        self.ParameterList = [GenericParams, 
                              SlopeParams, 
                              ReverseSlopeParams, 
                              PartialBlockParams, 
                              CoinParams, 
                              ExplodableBlockParams,
                              ClimableGridParams, 
                              SpikeParams,
                              PipeParams, 
                              RailParams, 
                              ConveyorBeltParams]
        
        
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.hexEditor, 0, 0, 1, 2)
        layout.addWidget(self.coreType, 1, 1)
        layout.addWidget(self.propertyGroup, 1, 0, 3, 1)
        layout.addWidget(self.parameters, 2, 1)
        layout.addWidget(self.terrainType, 3, 1)
        self.setLayout(layout)


    def hexEditorEdited(self):
        """
        The user changed some text in the hex editor
        """
        pass


    def swapParams(self):
        for item in range(11):
            if self.coreWidgets[item].isChecked():
                self.parameters.clear()
                for option in self.ParameterList[item]:
                    self.parameters.addItem(option[1], option[0])

    def currentData(self):
        """
        Returns the current data, in bytes format
        """
        rawstr = self.hexEditor.text()
        rawstr = rawstr.replace(' ', '')
        byte0 = int(rawstr[0 :2 ], 16)
        byte1 = int(rawstr[2 :4 ], 16)
        byte2 = int(rawstr[4 :6 ], 16)
        byte3 = int(rawstr[6 :8 ], 16)
        byte4 = int(rawstr[8 :10], 16)
        byte5 = int(rawstr[10:12], 16)
        byte6 = int(rawstr[12:14], 16)
        byte7 = int(rawstr[14:16], 16)
        return bytes([byte0, byte1, byte2, byte3, byte4, byte5, byte6, byte7])

        # REFERENCE --------------------------------------------------------------


        if self.coreWidgets[8].isChecked() or self.propertyWidgets[0].isChecked():
            solid = 1
        else:
            solid = 0
        
        if self.coreWidgets[1].isChecked() or self.coreWidgets[2].isChecked():
            solid = 0

        # Byte 0
        byte0 = 0
        # Byte 1
        byte1 = ((self.coreWidgets[8].isChecked()) +
            (self.propertyWidgets[2].isChecked() << 1) +
            (self.propertyWidgets[3].isChecked() << 3))
        # Byte 2
        byte2 = ((self.coreWidgets[6].isChecked() << 2) +
            (self.coreWidgets[3].isChecked() << 3) +
            (self.coreWidgets[7].isChecked() << 4) +
            (self.PassDown.isChecked() << 5) +
            (self.PassThrough.isChecked() << 7))
        # Byte 3
        byte3 = (solid + 
            (self.coreWidgets[4].isChecked() << 1) +
            (self.coreWidgets[5].isChecked() << 3) +
            (self.propertyWidgets[1].isChecked() << 4) +
            (self.coreWidgets[1].isChecked() << 5) +
            (self.coreWidgets[2].isChecked() << 6))
        # Byte 4
        byte4 = 0
        # Byte 5
        if self.coreWidgets[2].isChecked():
            byte5 = 4
        byte5 = self.terrainType.currentIndex()
        # Byte 6
        byte6 = 0
        # Byte 7
        if self.coreWidgets[0].isChecked():
            params = self.parameters.currentIndex()
            if params == 0:
                byte7 = 0
            elif params == 1:
                byte7 = 0x23
            elif params == 2:
                byte7 = 0x28
            elif params >= 3:
                byte7 = params + 0x32
        else:
            byte7 = self.parameters.currentIndex()
                    
            
            
##############################################################################################
##################### InfoBox Custom Widget to display info about a tile #####################
           
            
class InfoBox(QtWidgets.QGroupBox):
    def __init__(self, window):
        super().__init__(window)
        self.setTitle('Tile Information')
    
        # Create layout
        superLayout = QtWidgets.QGridLayout()
        
        # Create empty pixmaps
        self.transPix = QtGui.QPixmap(24, 24)
        self.transPix.fill(Qt.transparent)
        self.transBigPix = QtGui.QPixmap(96, 96)
        self.transBigPix.fill(Qt.transparent)

        # Create fonts
        Font = self.font()
        Font.setPointSize(9)
        global HexFont

        # Create static labels
        coreLabel = QtWidgets.QLabel('<b>Core</b>')
        terrLabel = QtWidgets.QLabel('<b>Terrain</b>')
        paramLabel = QtWidgets.QLabel('<b>Parameters</b>')

        # Create image labels
        self.tileImage = QtWidgets.QLabel()
        self.tileImage.setPixmap(self.transBigPix)
        self.coreImage = QtWidgets.QLabel()
        self.coreImage.setPixmap(self.transPix)
        self.terrainImage = QtWidgets.QLabel()
        self.terrainImage.setPixmap(self.transPix)
        self.parameterImage = QtWidgets.QLabel()
        self.parameterImage.setPixmap(self.transPix)
        
        # Create info labels
        self.posInfo = QtWidgets.QLabel('(none)')
        self.hexdata = QtWidgets.QLabel('0000 0000 0000 0000')
        self.coreInfo = QtWidgets.QLabel()
        self.propertyInfo = QtWidgets.QLabel()
        self.terrainInfo = QtWidgets.QLabel()
        self.paramInfo = QtWidgets.QLabel()

        # Set the fonts of the static labels
        coreLabel.setFont(Font)
        terrLabel.setFont(Font)
        paramLabel.setFont(Font)

        # Set the fonts of the info labels
        self.posInfo.setFont(Font)
        self.hexdata.setFont(HexFont)
        self.coreInfo.setFont(Font)
        self.propertyInfo.setFont(Font)
        self.terrainInfo.setFont(Font)
        self.paramInfo.setFont(Font)

        # Create a layout for the tile image and position label
        tileLayout = QtWidgets.QVBoxLayout()
        tileLayout.addWidget(self.tileImage)
        tileLayout.addWidget(self.posInfo)

        # Create the main layout and apply it
        superLayout.addLayout(tileLayout, 0, 0, 5, 1)
        superLayout.addWidget(self.hexdata, 0, 1, 1, 3)
        superLayout.addWidget(self.propertyInfo, 1, 1, 1, 3)
        superLayout.addWidget(coreLabel, 2, 1, Qt.AlignCenter)
        superLayout.addWidget(terrLabel, 2, 2, Qt.AlignCenter)
        superLayout.addWidget(paramLabel, 2, 3, Qt.AlignCenter)
        superLayout.addWidget(self.coreImage, 3, 1, Qt.AlignCenter)
        superLayout.addWidget(self.terrainImage, 3, 2, Qt.AlignCenter)
        superLayout.addWidget(self.parameterImage, 3, 3, Qt.AlignCenter)
        superLayout.addWidget(self.coreInfo, 4, 1, Qt.AlignCenter)
        superLayout.addWidget(self.terrainInfo, 4, 2, Qt.AlignCenter)
        superLayout.addWidget(self.paramInfo, 4, 3, Qt.AlignCenter)
        self.setLayout(superLayout)


    def updateInfo(self, tileIdx):
        """
        Updates the info for the tile at tileIdx
        If tileIdx is None, resets the labels
        """

        if tileIdx is None:
            posText = '(none) - (none)'
            hexText = '0000 0000 0000 0000'

            tilePix = self.transBigPix
            corePix = self.transPix
            terrainPix = self.transPix
            paramPix = self.transPix

            coreText = 'Default'
            propText = 'None'
            terrText = 'Default'
            paramText = 'None'
        else:
            curTile = Tileset.tiles[tileIdx]
            path = os.path.dirname(os.path.abspath(sys.argv[0])) + '/Icons/'

            propertyList = []
            coreType = 0
            palette = window.paletteWidget

            if curTile.byte3 & 32:
                coreType = 1
            elif curTile.byte3 & 64:
                coreType = 2
            elif curTile.byte2 & 8:
                coreType = 3
            elif curTile.byte3 & 2:
                coreType = 4
            elif curTile.byte3 & 8:
                coreType = 5
            elif curTile.byte2 & 4:
                coreType = 6
            elif curTile.byte2 & 16:
                coreType = 7
            elif curTile.byte1 & 1:
                coreType = 8
            elif 0 > curTile.byte7 > 0x23:
                coretype = 9
            elif curTile.byte5 == 4 or 5:
                coretype = 10    
            
            if curTile.byte3 & 1:
                propertyList.append('Solid')
            if curTile.byte3 & 16:
                propertyList.append('Breakable')
            if curTile.byte2 & 128:
                propertyList.append('Pass-Through')
            if curTile.byte2 & 32:
                propertyList.append('Pass-Down')
            if curTile.byte1 & 2:
                propertyList.append('Falling')
            if curTile.byte1 & 8:
                propertyList.append('Ledge')

            try:
                if coreType == 0:
                    if curTile.byte7 == 0x23:
                        parameter = palette.ParameterList[coreType][1]
                    elif curTile.byte7 == 0x28:
                        parameter = palette.ParameterList[coreType][2]
                    elif curTile.byte7 >= 0x35:
                        parameter = palette.ParameterList[coreType][curTile.byte7 - 0x32]
                    else:
                        parameter = palette.ParameterList[coreType][0]
                else:
                    parameter = palette.ParameterList[coreType][curTile.byte7]
            except IndexError: # a value is greater than the length of the list
                parameter = ['Unknown', QtGui.QIcon(path + 'Unknown.png')]

            posText = '({0}, {1}) - Tile {2}'.format(tileIdx % 16, tileIdx // 16, tileIdx)
            hexText = '{0:02x}{1:02x} {2:02x}{3:02x} {4:02x}{5:02x} {6:02x}{7:02x}'.format(
                curTile.byte0, curTile.byte1, curTile.byte2, curTile.byte3,
                curTile.byte4, curTile.byte5, curTile.byte6, curTile.byte7)

            if window.alpha:
                tilePix = curTile.image.scaled(96, 96)
            else:
                tilePix = curTile.noalpha.scaled(96, 96)
            try:
                corePix = palette.coreTypes[coreType][1].pixmap(24,24)
            except IndexError:
                corePix = QtGui.QPixmap(path + 'Unknown.png')
            try:
                terrainPix = palette.terrainTypes[curTile.byte5][1].pixmap(24,24)
            except IndexError:
                terrainPix = QtGui.QPixmap(path + 'Unknown.png')
            try:
                paramPix = parameter[1].pixmap(24,24)
            except IndexError:
                paramPix = QtGui.QPixmap(path + 'Unknown.png')

            try:
                coreText = palette.coreTypes[coreType][0]
            except IndexError:
                coreText = 'Unknown'
            if len(propertyList) == 0:
                propText = 'None'
            else:
                propText = ', '.join(propertyList)
            try:
                terrText = palette.terrainTypes[curTile.byte5][0]
            except IndexError:
                terrText = 'Unknown'
            paramText = parameter[0]

        self.posInfo.setText(posText)
        self.hexdata.setText(hexText)

        self.tileImage.setPixmap(tilePix)
        self.coreImage.setPixmap(corePix)
        self.terrainImage.setPixmap(terrainPix)
        self.parameterImage.setPixmap(paramPix)

        self.coreInfo.setText(coreText)
        self.propertyInfo.setText(propText)
        self.terrainInfo.setText(terrText)
        self.paramInfo.setText(paramText)
        
        self.update()
            


#############################################################################################
##################### Object List Widget and Model Setup with Painter #######################


class objectList(QtWidgets.QListView):
        
    def __init__(self, parent=None):
        super().__init__(parent)


        self.setViewMode(QtWidgets.QListView.IconMode)
        self.setIconSize(QtCore.QSize(96,96))
        self.setGridSize(QtCore.QSize(114,114))
        self.setMovement(QtWidgets.QListView.Static)
        self.setBackgroundRole(QtGui.QPalette.BrightText)
        self.setWrapping(False)
        self.setMinimumHeight(140)
        self.setMaximumHeight(140)

        

def SetupObjectModel(self, objects, tiles):
    global Tileset
    self.clear()
    
    count = 0
    for object in objects:
        tex = QtGui.QPixmap(object.width * 24, object.height * 24)
        tex.fill(Qt.transparent)
        painter = QtGui.QPainter(tex)
        
        Xoffset = 0
        Yoffset = 0
        
        for i in range(len(object.tiles)):
            for tile in object.tiles[i]:
                if (Tileset.slot == 0) or ((tile[2] & 3) != 0):
                    painter.drawPixmap(Xoffset, Yoffset, tiles[tile[1]].image)
                Xoffset += 24
            Xoffset = 0
            Yoffset += 24
                        
        painter.end()

        self.appendRow(QtGui.QStandardItem(QtGui.QIcon(tex), 'Object {0}'.format(count)))
    
        count += 1


#############################################################################################
######################## List Widget with custom painter/MouseEvent #########################


class displayWidget(QtWidgets.QListView):
    
    mouseMoved = QtCore.pyqtSignal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Fixed,
                QtWidgets.QSizePolicy.Fixed,
                )
            )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setDragEnabled(True)
        self.setDragDropMode(self.DragDrop)
        self.setViewMode(QtWidgets.QListView.IconMode)
        self.setIconSize(QtCore.QSize(24,24))
        self.setGridSize(QtCore.QSize(25,25))
        #self.setMovement(QtWidgets.QListView.Static)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(True)
        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setUniformItemSizes(True)
        self.setBackgroundRole(QtGui.QPalette.BrightText)
        self.setMouseTracking(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        p =  self.palette()
        p.setBrush(p.Base, self.BackgroundBrush())
        self.setPalette(p)

        self.setItemDelegate(self.TileItemDelegate())


    def sizeHint(self):
        """
        Reimplementation of sizeHint
        """
        return QtCore.QSize(
            384 + 15 + 6,
            384 + 15 + 6,
            )

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        self.mouseMoved.emit(event.x(), event.y())
        self.update()


    def BackgroundBrush(self):
        """
        Returns the background brush
        """
        color1 = Qt.white
        color2 = QtGui.QColor.fromRgb(230, 230, 230)

        pix = QtGui.QPixmap(25, 25)
        pix.fill(color1)

        paint = QtGui.QPainter(pix)
        paint.setPen(Qt.NoPen)
        paint.setBrush(QtGui.QBrush(color2))
        paint.drawRect(0, 0, 12, 12)
        paint.drawRect(12, 12, 25, 25)
        del paint

        brush = QtGui.QBrush(pix)
        return brush



    class TileItemDelegate(QtWidgets.QAbstractItemDelegate):
        """Handles tiles and their rendering"""

        def __init__(self):
            """Initialises the delegate"""
            QtWidgets.QAbstractItemDelegate.__init__(self)

        def paint(self, painter, option, index):
            """Paints an object"""

            global Tileset
            p = index.model().data(index, Qt.DecorationRole)
            painter.drawPixmap(option.rect.x(), option.rect.y(), p.pixmap(24,24))

            x = option.rect.x()
            y = option.rect.y()


            # Collision Overlays
            info = window.infoDisplay
            try:
                curTile = Tileset.tiles[index.row()]
            except IndexError:
                # uh oh
                return
            
            if window.collision:
                path = os.path.dirname(os.path.abspath(sys.argv[0])) + '/Icons/'
                
                # Sets the color based on terrain type
                if curTile.byte2 & 16:      # Red
                    color = QtGui.QColor(255, 0, 0, 120)                    
                elif curTile.byte5 == 1:    # Ice
                    color = QtGui.QColor(0, 0, 255, 120)
                elif curTile.byte5 == 2:    # Snow
                    color = QtGui.QColor(0, 0, 255, 120)
                elif curTile.byte5 == 3:    # Quicksand
                    color = QtGui.QColor(128,64,0, 120)
                elif curTile.byte5 == 4:    # Conveyor
                    color = QtGui.QColor(128,128,128, 120)
                elif curTile.byte5 == 5:    # Conveyor
                    color = QtGui.QColor(128,128,128, 120)
                elif curTile.byte5 == 6:    # Rope
                    color = QtGui.QColor(128,0,255, 120)
                elif curTile.byte5 == 7:    # Half Spike
                    color = QtGui.QColor(128,0,255, 120)
                elif curTile.byte5 == 8:    # Ledge
                    color = QtGui.QColor(128,0,255, 120)
                elif curTile.byte5 == 9:    # Ladder
                    color = QtGui.QColor(128,0,255, 120)
                elif curTile.byte5 == 10:    # Staircase
                    color = QtGui.QColor(255, 0, 0, 120)
                elif curTile.byte5 == 11:    # Carpet
                    color = QtGui.QColor(255, 0, 0, 120)
                elif curTile.byte5 == 12:    # Dust
                    color = QtGui.QColor(128,64,0, 120)
                elif curTile.byte5 == 13:    # Grass
                    color = QtGui.QColor(0, 255, 0, 120)
                elif curTile.byte5 == 14:    # Unknown
                    color = QtGui.QColor(255, 0, 0, 120)
                elif curTile.byte5 == 15:    # Beach Sand
                    color = QtGui.QColor(128, 64, 0, 120)
                else:                       # Brown?
                    color = QtGui.QColor(64, 30, 0, 120)


                # Sets Brush style for fills
                if curTile.byte2 & 4:        # Climbing Grid
                    style = Qt.DiagCrossPattern
                elif curTile.byte3 & 16:     # Breakable
                    style = Qt.VerPattern
                else:
                    style = Qt.SolidPattern


                brush = QtGui.QBrush(color, style)
                painter.setBrush(brush)
                painter.setRenderHint(QtGui.QPainter.Antialiasing)


                # Paints shape based on other junk
                if curTile.byte3 & 32: # Slope
                    if curTile.byte7 == 0:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y)]))
                    elif curTile.byte7 == 1:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 2:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y + 12)]))
                    elif curTile.byte7 == 3:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x, y + 12),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 24)]))
                    elif curTile.byte7 == 4:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x + 24, y + 24)]))
                    elif curTile.byte7 == 5:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 12),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 10:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y)]))
                    elif curTile.byte7 == 11:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x + 24, y + 18),
                                                            QtCore.QPoint(x + 24, y + 24)]))
                    elif curTile.byte7 == 12:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x, y + 18),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 13:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y + 6),
                                                            QtCore.QPoint(x, y + 12),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 14:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x, y + 6),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 15:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y + 6),
                                                            QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 16:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x, y + 6),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 17:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y + 18),
                                                            QtCore.QPoint(x, y + 12),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 18:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x, y + 18),
                                                            QtCore.QPoint(x, y + 24)]))

                elif curTile.byte3 & 64: # Reverse Slope
                    if curTile.byte7 == 0:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y)]))
                    elif curTile.byte7 == 1:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y)]))
                    elif curTile.byte7 == 2:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y + 12)]))
                    elif curTile.byte7 == 3:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x, y + 12),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y)]))
                    elif curTile.byte7 == 4:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 12)]))
                    elif curTile.byte7 == 5:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 12),
                                                            QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y)]))
                    elif curTile.byte7 == 10:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y)]))
                    elif curTile.byte7 == 11:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 6)]))
                    elif curTile.byte7 == 12:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x, y + 6)]))
                    elif curTile.byte7 == 13:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 18),
                                                            QtCore.QPoint(x, y + 12)]))
                    elif curTile.byte7 == 14:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x, y + 18)]))
                    elif curTile.byte7 == 15:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 18),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 16:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x, y + 18)]))
                    elif curTile.byte7 == 17:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 6),
                                                            QtCore.QPoint(x, y + 12)]))
                    elif curTile.byte7 == 18:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x, y + 6)]))

                elif curTile.byte2 & 8: # Partial
                    if curTile.byte7 == 1:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 12, y),
                                                            QtCore.QPoint(x + 12, y + 12),
                                                            QtCore.QPoint(x, y + 12)]))
                    elif curTile.byte7 == 2:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 12, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x + 12, y + 12)]))
                    elif curTile.byte7 == 3:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x, y + 12)]))
                    elif curTile.byte7 == 4:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 12),
                                                            QtCore.QPoint(x + 12, y + 12),
                                                            QtCore.QPoint(x + 12, y + 24),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 5:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 12, y),
                                                            QtCore.QPoint(x + 12, y + 24),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 6:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x + 12, y + 24),
                                                            QtCore.QPoint(x + 12, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x, y + 12)]))
                    elif curTile.byte7 == 7:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x + 12, y + 12),
                                                            QtCore.QPoint(x + 12, y + 24),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 8:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 12, y + 12),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 12, y + 24)]))
                    elif curTile.byte7 == 9:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x, y + 12),
                                                            QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x + 12, y + 24),
                                                            QtCore.QPoint(x + 12, y)]))
                    elif curTile.byte7 == 10:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 12, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 12, y + 24)]))
                    elif curTile.byte7 == 11:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 12, y + 24),
                                                            QtCore.QPoint(x + 12, y + 12),
                                                            QtCore.QPoint(x, y + 12)]))
                    elif curTile.byte7 == 12:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 12),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 13:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 12, y),
                                                            QtCore.QPoint(x + 12, y + 12),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 14:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 12, y),
                                                            QtCore.QPoint(x + 12, y + 12),
                                                            QtCore.QPoint(x, y + 12),
                                                            QtCore.QPoint(x, y + 24)]))
                    elif curTile.byte7 == 15:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x, y + 24)]))

                elif curTile.byte2 & 0x20: # Solid-on-bottom
                    painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 24),
                                                        QtCore.QPoint(x + 24, y + 24),
                                                        QtCore.QPoint(x + 24, y + 18),
                                                        QtCore.QPoint(x, y + 18)]))

                    painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 15, y),
                                                        QtCore.QPoint(x + 15, y + 12),
                                                        QtCore.QPoint(x + 18, y + 12),
                                                        QtCore.QPoint(x + 12, y + 17),
                                                        QtCore.QPoint(x + 6, y + 12),
                                                        QtCore.QPoint(x + 9, y + 12),
                                                        QtCore.QPoint(x + 9, y)]))

                elif curTile.byte2 & 0x80: # Solid-on-top
                    painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                        QtCore.QPoint(x + 24, y),
                                                        QtCore.QPoint(x + 24, y + 6),
                                                        QtCore.QPoint(x, y + 6)]))

                    painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 15, y + 24),
                                                        QtCore.QPoint(x + 15, y + 12),
                                                        QtCore.QPoint(x + 18, y + 12),
                                                        QtCore.QPoint(x + 12, y + 7),
                                                        QtCore.QPoint(x + 6, y + 12),
                                                        QtCore.QPoint(x + 9, y + 12),
                                                        QtCore.QPoint(x + 9, y + 24)]))

                elif curTile.byte2 & 16: # Spikes
                    if curTile.byte7 == 0:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x, y + 6)]))
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 24, y + 12),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x, y + 18)]))
                    if curTile.byte7 == 1:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x, y + 12),
                                                            QtCore.QPoint(x + 24, y + 6)]))
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 12),
                                                            QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x + 24, y + 18)]))
                    if curTile.byte7 == 2:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y + 24),
                                                            QtCore.QPoint(x + 12, y + 24),
                                                            QtCore.QPoint(x + 6, y)]))
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 12, y + 24),
                                                            QtCore.QPoint(x + 24, y + 24),
                                                            QtCore.QPoint(x + 18, y)]))
                    if curTile.byte7 == 3:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 12, y),
                                                            QtCore.QPoint(x + 6, y + 24)]))
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 12, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 18, y + 24)]))
                    if curTile.byte7 == 4:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 18, y + 24),
                                                            QtCore.QPoint(x + 6, y + 24)]))
                    if curTile.byte7 == 5:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x + 6, y),
                                                            QtCore.QPoint(x + 18, y),
                                                            QtCore.QPoint(x + 12, y + 24)]))
                    if curTile.byte7 == 6:
                        painter.drawPolygon(QtGui.QPolygon([QtCore.QPoint(x, y),
                                                            QtCore.QPoint(x + 24, y),
                                                            QtCore.QPoint(x + 12, y + 24)]))

                elif curTile.byte3 & 4: # QBlock
                    if curTile.byte7 == 0:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'QBlock/FireF.png'))
                    if curTile.byte7 == 1:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'QBlock/Star.png'))
                    if curTile.byte7 == 2:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'QBlock/Coin.png'))
                    if curTile.byte7 == 3:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'QBlock/Vine.png'))
                    if curTile.byte7 == 4:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'QBlock/1up.png'))
                    if curTile.byte7 == 5:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'QBlock/Mini.png'))
                    if curTile.byte7 == 6:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'QBlock/Prop.png'))
                    if curTile.byte7 == 7:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'QBlock/Peng.png'))                    
                    if curTile.byte7 == 8:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'QBlock/IceF.png'))

                elif curTile.byte3 & 2: # Coin
                    if curTile.byte7 == 0:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'Coin/Coin.png'))
                    if curTile.byte7 == 4:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'Coin/POW.png'))

                elif curTile.byte3 & 8: # Exploder
                    if curTile.byte7 == 1:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'Explode/Stone.png'))
                    if curTile.byte7 == 2:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'Explode/Wood.png'))
                    if curTile.byte7 == 3:
                        painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'Explode/Red.png'))

                elif curTile.byte1 & 2: # Falling
                    painter.drawPixmap(option.rect, QtGui.QPixmap(path + 'Prop/Fall.png'))

#                elif curTile.byte5 == 4 or 5: # Conveyor
#                    d

                elif curTile.byte3 & 1: # Solid
                    painter.drawRect(option.rect)

                else: # No fill
                    pass
                                

            # Highlight stuff. 
            color = QtGui.QColor(option.palette.highlight())
            color.setAlpha(80)

            if option.state & QtWidgets.QStyle.State_Selected:
                painter.fillRect(option.rect, color)
            
        
        def sizeHint(self, option, index):
            """
            Return the size for the object
            """
            return QtCore.QSize(24,24)
        
        
        
#############################################################################################
############################ Tile widget for drag n'drop Objects ############################


class tileOverlord(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Setup Widgets
        self.tiles = tileWidget()

        self.addObject = QtWidgets.QPushButton('Add')
        self.removeObject = QtWidgets.QPushButton('Remove')

        self.addRow = QtWidgets.QPushButton('+')
        self.removeRow = QtWidgets.QPushButton('-')
    
        self.addColumn = QtWidgets.QPushButton('+')
        self.removeColumn = QtWidgets.QPushButton('-')

        self.tilingMethod = QtWidgets.QComboBox()
        self.tilesetType = QtWidgets.QLabel('Pa1')

        self.tilingMethod.addItems(['Repeat', 
                                    'Stretch Center',
                                    'Stretch X',
                                    'Stretch Y',
                                    'Repeat Bottom',
                                    'Repeat Top',
                                    'Repeat Left',
                                    'Repeat Right',
                                    'Upward slope',
                                    'Downward slope',
                                    'Downward reverse slope',
                                    'Upward reverse slope'])


        # Connections
        self.addObject.released.connect(self.addObj)
        self.removeObject.released.connect(self.removeObj)
        self.addRow.released.connect(self.tiles.addRow)
        self.removeRow.released.connect(self.tiles.removeRow)
        self.addColumn.released.connect(self.tiles.addColumn)
        self.removeColumn.released.connect(self.tiles.removeColumn)

        self.tilingMethod.activated.connect(self.setTiling)


        # Layout
        layout = QtWidgets.QGridLayout()        
        
        layout.addWidget(self.tilesetType, 0, 0, 1, 3)
        layout.addWidget(self.tilingMethod, 0, 3, 1, 3)

        layout.addWidget(self.addObject, 0, 6, 1, 1)
        layout.addWidget(self.removeObject, 0, 7, 1, 1)
        
        layout.setRowMinimumHeight(1, 40)
        
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 5)
        layout.setRowStretch(5, 5)
        layout.addWidget(self.tiles, 2, 1, 4, 6)
        
        layout.addWidget(self.addColumn, 3, 7, 1, 1)
        layout.addWidget(self.removeColumn, 4, 7, 1, 1)
        layout.addWidget(self.addRow, 6, 3, 1, 1)
        layout.addWidget(self.removeRow, 6, 4, 1, 1)
        
        self.setLayout(layout)
       



    def addObj(self):
        global Tileset
        
        Tileset.addObject()
        
        pix = QtGui.QPixmap(24, 24)
        pix.fill(Qt.transparent)
        painter = QtGui.QPainter(pix)
        painter.drawPixmap(0, 0, Tileset.tiles[0].image)
        painter.end()
                    
        count = len(Tileset.objects)
        window.objmodel.appendRow(QtGui.QStandardItem(QtGui.QIcon(pix), 'Object {0}'.format(count-1)))
        index = window.objectList.currentIndex()
        window.objectList.setCurrentIndex(index)
        self.setObject(index)

        window.objectList.update()
        self.update()
        

    def removeObj(self):
        global Tileset

        index = window.objectList.currentIndex()

        Tileset.removeObject(index.row())
        window.objmodel.removeRow(index.row())
        self.tiles.clear()

        window.objectList.update()
        self.update()


    def setObject(self, index):
        global Tileset
        object = Tileset.objects[index.row()]
                
        width = len(object.tiles[0])-1
        height = len(object.tiles)-1
        Xuniform = True
        Yuniform = True
        Xstretch = False
        Ystretch = False

        for tile in object.tiles[0]:
            if tile[0] != object.tiles[0][0][0]:
                Xuniform = False
                
        for tile in object.tiles:
            if tile[0][0] != object.tiles[0][0][0]:
                Yuniform = False

        if object.tiles[0][0][0] == object.tiles[0][width][0] and Xuniform == False:
            Xstretch = True

        if object.tiles[0][0][0] == object.tiles[height][0][0] and Xuniform == False:
            Ystretch = True



        if object.upperslope[0] != 0:
            if object.upperslope[0] == 0x90:
                self.tilingMethod.setCurrentIndex(8)
            elif object.upperslope[0] == 0x91:
                self.tilingMethod.setCurrentIndex(9)
            elif object.upperslope[0] == 0x92:
                self.tilingMethod.setCurrentIndex(10)
            elif object.upperslope[0] == 0x93:
                self.tilingMethod.setCurrentIndex(11)
            
        else:
            if Xuniform and Yuniform:
                self.tilingMethod.setCurrentIndex(0)
            elif Xstretch and Ystretch:
                self.tilingMethod.setCurrentIndex(1)
            elif Xstretch:
                self.tilingMethod.setCurrentIndex(2)
            elif Ystretch:
                self.tilingMethod.setCurrentIndex(3)
            elif Xuniform and Yuniform == False and object.tiles[0][0][0] == 0:
                self.tilingMethod.setCurrentIndex(4)
            elif Xuniform and Yuniform == False and object.tiles[height][0][0] == 0:
                self.tilingMethod.setCurrentIndex(5)
            elif Xuniform == False and Yuniform and object.tiles[0][0][0] == 0:
                self.tilingMethod.setCurrentIndex(6)
            elif Xuniform == False and Yuniform and object.tiles[0][width][0] == 0:
                self.tilingMethod.setCurrentIndex(7)

                
        self.tiles.setObject(object)

#        print(Object {0}, Width: {1} / Height: {2}, Slope {3}/{4}'.format(index.row(), object.width, object.height, object.upperslope, object.lowerslope))
#        for row in object.tiles:
#            print('Row: {0}'.format(row))
#        print('')
    
    @QtCore.pyqtSlot(int)
    def setTiling(self, listindex):
        global Tileset
        
        index = window.objectList.currentIndex()
        object = Tileset.objects[index.row()]
        
        
        if listindex == 0: # Repeat
            ctile = 0
            crow = 0

            for row in object.tiles:
                for tile in row:
                    object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    ctile += 1
                crow += 1
                ctile = 0
                
        if listindex == 1: # Stretch Center

            if object.width < 3 and object.height < 3:
                reply = QtWidgets.QMessageBox.information(self, 'Warning', 'An object must be at least 3 tiles\nwide and 3 tiles tall to apply stretch center.')
                self.setObject(index)
                return
                
            ctile = 0
            crow = 0

            for row in object.tiles:
                for tile in row:
                    if crow == 0 and ctile == 0:
                        object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    elif crow == 0 and ctile == object.width-1:
                        object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    elif crow == object.height-1 and ctile == object.width-1:
                        object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    elif crow == object.height-1 and ctile == 0:
                        object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    elif crow == 0 or crow == object.height-1:
                        object.tiles[crow][ctile] = (1, tile[1], tile[2])
                    elif ctile == 0 or ctile == object.width-1:
                        object.tiles[crow][ctile] = (2, tile[1], tile[2])
                    else:
                        object.tiles[crow][ctile] = (3, tile[1], tile[2])
                    ctile += 1
                crow += 1
                ctile = 0
                
            object.upperslope = [0, 0]
            object.lowerslope = [0, 0]

        if listindex == 2: # Stretch X

            if object.width < 3:
                reply = QtWidgets.QMessageBox.information(self, 'Warning', 'An object must be at least 3 tiles\nwide to apply stretch X.')
                self.setObject(index)
                return
                
            ctile = 0
            crow = 0

            for row in object.tiles:
                for tile in row:
                    if ctile == 0:
                        object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    elif ctile == object.width-1:
                        object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    else:
                        object.tiles[crow][ctile] = (1, tile[1], tile[2])
                    ctile += 1
                crow += 1
                ctile = 0
                 
            object.upperslope = [0, 0]
            object.lowerslope = [0, 0]
               
        if listindex == 3: # Stretch Y

            if object.height < 3:
                reply = QtWidgets.QMessageBox.information(self, 'Warning', 'An object must be at least 3 tiles\ntall to apply stretch Y.')
                self.setObject(index)
                return
                
            ctile = 0
            crow = 0

            for row in object.tiles:
                for tile in row:
                    if crow == 0:
                        object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    elif crow == object.height-1:
                        object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    else:
                        object.tiles[crow][ctile] = (2, tile[1], tile[2])
                    ctile += 1
                crow += 1
                ctile = 0
                
            object.upperslope = [0, 0]
            object.lowerslope = [0, 0]
                
        if listindex == 4: # Repeat Bottom

            if object.height < 2:
                reply = QtWidgets.QMessageBox.information(self, 'Warning', 'An object must be at least 2 tiles\ntall to apply repeat bottom.')
                self.setObject(index)
                return
                
            ctile = 0
            crow = 0

            for row in object.tiles:
                for tile in row:
                    if crow == object.height-1:
                        object.tiles[crow][ctile] = (2, tile[1], tile[2])
                    else:
                        object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    ctile += 1
                crow += 1
                ctile = 0
                
            object.upperslope = [0, 0]
            object.lowerslope = [0, 0]

        if listindex == 5: # Repeat Top

            if object.height < 2:
                reply = QtWidgets.QMessageBox.information(self, 'Warning', 'An object must be at least 2 tiles\ntall to apply repeat top.')
                self.setObject(index)
                return
                
            ctile = 0
            crow = 0

            for row in object.tiles:
                for tile in row:
                    if crow == 0:
                        object.tiles[crow][ctile] = (2, tile[1], tile[2])
                    else:
                        object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    ctile += 1
                crow += 1
                ctile = 0
                
            object.upperslope = [0, 0]
            object.lowerslope = [0, 0]

        if listindex == 6: # Repeat Left

            if object.width < 2:
                reply = QtWidgets.QMessageBox.information(self, 'Warning', 'An object must be at least 2 tiles\nwide to apply repeat left.')
                self.setObject(index)
                return
                
            ctile = 0
            crow = 0

            for row in object.tiles:
                for tile in row:
                    if ctile == 0:
                        object.tiles[crow][ctile] = (1, tile[1], tile[2])
                    else:
                        object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    ctile += 1
                crow += 1
                ctile = 0
                
            object.upperslope = [0, 0]
            object.lowerslope = [0, 0]

        if listindex == 7: # Repeat Right

            if object.width < 2:
                reply = QtWidgets.QMessageBox.information(self, 'Warning', 'An object must be at least 2 tiles\nwide to apply repeat right.')
                self.setObject(index)
                return
                
            ctile = 0
            crow = 0

            for row in object.tiles:
                for tile in row:
                    if ctile == object.width-1:
                        object.tiles[crow][ctile] = (1, tile[1], tile[2])
                    else:
                        object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    ctile += 1
                crow += 1
                ctile = 0
                
            object.upperslope = [0, 0]
            object.lowerslope = [0, 0]


        if listindex == 8: # Upward Slope
            ctile = 0
            crow = 0
            for row in object.tiles:
                for tile in row:
                    object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    ctile += 1
                crow += 1
                ctile = 0

            object.upperslope = [0x90, 1]
            object.lowerslope = [0x84, object.height - 1]
            self.tiles.slope = 1
            
            self.tiles.update()
            
        if listindex == 9: # Downward Slope
            ctile = 0
            crow = 0
            for row in object.tiles:
                for tile in row:
                    object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    ctile += 1
                crow += 1
                ctile = 0

            object.upperslope = [0x91, 1]
            object.lowerslope = [0x84, object.height - 1]
            self.tiles.slope = 1
            
            self.tiles.update()

        if listindex == 10: # Upward Reverse Slope
            ctile = 0
            crow = 0
            for row in object.tiles:
                for tile in row:
                    object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    ctile += 1
                crow += 1
                ctile = 0

            object.upperslope = [0x92, object.height - 1]
            object.lowerslope = [0x84, 1]
            self.tiles.slope = 0-(object.height-1)
            
            self.tiles.update()

        if listindex == 11: # Downward Reverse Slope
            ctile = 0
            crow = 0
            for row in object.tiles:
                for tile in row:
                    object.tiles[crow][ctile] = (0, tile[1], tile[2])
                    ctile += 1
                crow += 1
                ctile = 0

            object.upperslope = [0x93, object.height - 1]
            object.lowerslope = [0x84, 1]
            self.tiles.slope = 0-(object.height-1)
            
            self.tiles.update()
       

class tileWidget(QtWidgets.QWidget):
    
    def __init__(self):
        super().__init__()

        self.tiles = []

        self.size = [1, 1]
        self.setMinimumSize(24, 24)

        self.slope = 0

        self.highlightedRect = QtCore.QRect()

        self.setAcceptDrops(True)
        self.object = 0


    def clear(self):
        self.tiles = []
        self.size = [1, 1] # [width, height]
        
        self.slope = 0
        self.highlightedRect = QtCore.QRect()

        self.update()


    def addColumn(self):
        global Tileset
        
        if self.size[0] >= 24:
            return
            
        self.size[0] += 1
        self.setMinimumSize(self.size[0]*24, self.size[1]*24)

        pix = QtGui.QPixmap(24,24)
        pix.fill(QtGui.QColor(0,0,0,0))

        for y in range(self.size[1]):
            self.tiles.insert(((y+1) * self.size[0]) -1, [self.size[0]-1, y, pix])

 
        curObj = Tileset.objects[self.object]
        curObj.width += 1

        for row in curObj.tiles:
            row.append((0, 0, 0))
            
        self.update()
        self.updateList()

   
    def removeColumn(self):
        global Tileset

        if self.size[0] == 1:
            return

        for y in range(self.size[1]):
            self.tiles.pop(((y+1) * self.size[0])-(y+1))

        self.size[0] = self.size[0] - 1
        self.setMinimumSize(self.size[0]*24, self.size[1]*24)


        curObj = Tileset.objects[self.object]
        curObj.width -= 1

        for row in curObj.tiles:
            row.pop()

        self.update()
        self.updateList()


    def addRow(self):
        global Tileset

        if self.size[1] >= 24:
            return
        
        self.size[1] += 1
        self.setMinimumSize(self.size[0]*24, self.size[1]*24)

        pix = QtGui.QPixmap(24,24)
        pix.fill(QtGui.QColor(0,0,0,0))

        for x in range(self.size[0]):
            self.tiles.append([x, self.size[1]-1, pix])

        curObj = Tileset.objects[self.object]
        curObj.height += 1

        curObj.tiles.append([])
        for i in range(0, curObj.width):
            curObj.tiles[len(curObj.tiles)-1].append((0, 0, 0))

        self.update()
        self.updateList()

    
    def removeRow(self):
        global Tileset

        if self.size[1] == 1:
            return

        for x in range(self.size[0]):
            self.tiles.pop()
        
        self.size[1] -= 1
        self.setMinimumSize(self.size[0]*24, self.size[1]*24)

        curObj = Tileset.objects[self.object]
        curObj.height -= 1

        curObj.tiles.pop()

        self.update()
        self.updateList()


    def setObject(self, object):
        self.clear()
            
        global Tileset
            
        self.size = [object.width, object.height]
        
        if not object.upperslope[1] == 0:
            if object.upperslope[0] & 2:
                self.slope = 0 - object.lowerslope[1]
            else:
                self.slope = object.upperslope[1]

        x = 0
        y = 0
        for row in object.tiles:
            for tile in row:
                if (Tileset.slot == 0) or ((tile[2] & 3) != 0):
                    self.tiles.append([x, y, Tileset.tiles[tile[1]].image])
                else:
                    pix = QtGui.QPixmap(24,24)
                    pix.fill(QtGui.QColor(0,0,0,0))
                    self.tiles.append([x, y, pix])
                x += 1
            y += 1
            x = 0
           
           
        self.object = window.objectList.currentIndex().row()    
        self.update()
        self.updateList()
               

    def contextMenuEvent(self, event):
    
        TileMenu = QtWidgets.QMenu(self)
        self.contX = event.x()
        self.contY = event.y()
        
        TileMenu.addAction('Set Tile...', self.setTile)
        TileMenu.addAction('Add Item...', self.setItem)

        TileMenu.exec_(event.globalPos())


    def mousePressEvent(self, event):
        global Tileset

        if event.button() == 2:
            return

        if window.tileDisplay.selectedIndexes() == []:
            return

        currentSelected = window.tileDisplay.selectedIndexes()
        
        ix = 0
        iy = 0
        for modelItem in currentSelected:
            # Update yourself!
            centerPoint = self.contentsRect().center()
    
            tile = modelItem.row()
            upperLeftX = centerPoint.x() - self.size[0]*12
            upperLeftY = centerPoint.y() - self.size[1]*12
    
            lowerRightX = centerPoint.x() + self.size[0]*12
            lowerRightY = centerPoint.y() + self.size[1]*12
    
    
            x = (event.x() - upperLeftX)/24 + ix
            y = (event.y() - upperLeftY)/24 + iy
            x, y = int(x), int(y)
    
            if event.x() < upperLeftX or event.y() < upperLeftY or event.x() > lowerRightX or event.y() > lowerRightY:
                return
                    
            self.tiles[(y * self.size[0]) + x][2] = Tileset.tiles[tile].image
                    
            Tileset.objects[self.object].tiles[y][x] = (Tileset.objects[self.object].tiles[y][x][0], tile, Tileset.slot)
            

            ix += 1
            if self.size[0]-1 < ix:
                ix = 0
                iy += 1
            if iy > self.size[1]-1:
                break
            
            
        self.update()
        
        self.updateList()
        

    def updateList(self):        
        # Update the list >.>
        object = window.objmodel.itemFromIndex(window.objectList.currentIndex())
        if object is None: return
        
        
        tex = QtGui.QPixmap(self.size[0] * 24, self.size[1] * 24)
        tex.fill(Qt.transparent)
        painter = QtGui.QPainter(tex)
        
        Xoffset = 0
        Yoffset = 0
        
        for tile in self.tiles:
            painter.drawPixmap(tile[0]*24, tile[1]*24, tile[2])
                        
        painter.end()

        object.setIcon(QtGui.QIcon(tex))

        window.objectList.update()
    
            
        
    def setTile(self):
        global Tileset
        
        dlg = self.setTileDialog()
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            # Do stuff
            centerPoint = self.contentsRect().center()

            upperLeftX = centerPoint.x() - self.size[0]*12
            upperLeftY = centerPoint.y() - self.size[1]*12

            tile = dlg.tile.value()
            tileset = dlg.tileset.currentIndex()
    
            x = (self.contX - upperLeftX)/24
            y = (self.contY - upperLeftY)/24

            if tileset != Tileset.slot:
                tex = QtGui.QPixmap(self.size[0] * 24, self.size[1] * 24)
                tex.fill(Qt.transparent)
        
                self.tiles[(y * self.size[0]) + x][2] = tex

            Tileset.objects[self.object].tiles[y][x] = (Tileset.objects[self.object].tiles[y][x][0], tile, tileset)
            
            self.update()
            self.updateList()


    class setTileDialog(QtWidgets.QDialog):
    
        def __init__(self):
            QtWidgets.QDialog.__init__(self)
        
            self.setWindowTitle('Set tiles')
        
            self.tileset = QtWidgets.QComboBox()
            self.tileset.addItems(['Pa0', 'Pa1', 'Pa2', 'Pa3'])
        
            self.tile = QtWidgets.QSpinBox()                
            self.tile.setRange(0, 255)             
            
            self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
            self.buttons.accepted.connect(self.accept)
            self.buttons.rejected.connect(self.reject)
            
            self.layout = QtWidgets.QGridLayout()
            self.layout.addWidget(QtWidgets.QLabel('Tileset:'), 0,0,1,1, Qt.AlignLeft)
            self.layout.addWidget(QtWidgets.QLabel('Tile:'), 0,3,1,1, Qt.AlignLeft)
            self.layout.addWidget(self.tileset, 1, 0, 1, 2)
            self.layout.addWidget(self.tile, 1, 3, 1, 3)
            self.layout.addWidget(self.buttons, 2, 3)
            self.setLayout(self.layout)


    def setItem(self):
        global Tileset
        
        dlg = self.setItemDialog()
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            # Do stuff
            centerPoint = self.contentsRect().center()

            upperLeftX = centerPoint.x() - self.size[0]*12
            upperLeftY = centerPoint.y() - self.size[1]*12

            item = dlg.item.currentIndex()
    
            x = (self.contX - upperLeftX)/24
            y = (self.contY - upperLeftY)/24

            obj = Tileset.objects[self.object].tiles[y][x]
            
            obj = (obj[0], obj[1], obj[2] | (item << 2))
            
            self.update()
            self.updateList()


    class setItemDialog(QtWidgets.QDialog):
    
        def __init__(self):
            QtWidgets.QDialog.__init__(self)
        
            self.setWindowTitle('Set item')
        
            self.item = QtWidgets.QComboBox()
            self.item.addItems(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14'])
                    
            self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
            self.buttons.accepted.connect(self.accept)
            self.buttons.rejected.connect(self.reject)
            
            self.layout = QtWidgets.QHBoxLayout()
            self.vlayout = QtWidgets.QVBoxLayout()
            self.layout.addWidget(QtWidgets.QLabel('Item:'))
            self.layout.addWidget(self.item)
            self.vlayout.addLayout(self.layout)
            self.vlayout.addWidget(self.buttons)
            self.setLayout(self.vlayout)
            
               

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        
        centerPoint = self.contentsRect().center()
        upperLeftX = centerPoint.x() - self.size[0]*12
        lowerRightX = centerPoint.x() + self.size[0]*12

        upperLeftY = centerPoint.y() - self.size[1]*12
        lowerRightY = centerPoint.y() + self.size[1]*12


        painter.fillRect(upperLeftX, upperLeftY, self.size[0] * 24, self.size[1]*24, QtGui.QColor(205, 205, 255))

        for x, y, pix in self.tiles:
            painter.drawPixmap(upperLeftX + (x * 24), upperLeftY + (y * 24), pix)

        if not self.slope == 0:
            pen = QtGui.QPen()
#            pen.setStyle(Qt.QDashLine)
            pen.setWidth(1)
            pen.setColor(Qt.blue)
            painter.setPen(QtGui.QPen(pen))
            painter.drawLine(upperLeftX, upperLeftY + (abs(self.slope) * 24), lowerRightX, upperLeftY + (abs(self.slope) * 24))
            
            if self.slope > 0:
                main = 'Main'
                sub = 'Sub'
            elif self.slope < 0:
                main = 'Sub'
                sub = 'Main'

            font = painter.font()
            font.setPixelSize(8)
            font.setFamily('Monaco')
            painter.setFont(font)

            painter.drawText(upperLeftX+1, upperLeftY+10, main)
            painter.drawText(upperLeftX+1, upperLeftY + (abs(self.slope) * 24) + 9, sub)

        painter.end()



#############################################################################################
############################ Subclassed one dimension Item Model ############################


class PiecesModel(QtCore.QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.pixmaps = []

    def supportedDragActions(self):
        super().supportedDragActions()
        return Qt.CopyAction | Qt.MoveAction | Qt.LinkAction

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DecorationRole:
            return QtGui.QIcon(self.pixmaps[index.row()])

        if role == Qt.UserRole:
            return self.pixmaps[index.row()]

        return None

    def addPieces(self, pixmap):
        row = len(self.pixmaps)

        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self.pixmaps.insert(row, pixmap)
        self.endInsertRows()
        
    def flags(self, index):
        if index.isValid():
            return (Qt.ItemIsEnabled | Qt.ItemIsSelectable |
                    Qt.ItemIsDragEnabled)

    def clear(self):
        row = len(self.pixmaps)

        del self.pixmaps[:]


    def mimeTypes(self):
        return ['image/x-tile-piece']


    def mimeData(self, indexes):
        mimeData = QtCore.QMimeData()
        encodedData = QtCore.QByteArray()

        stream = QtCore.QDataStream(encodedData, QtCore.QIODevice.WriteOnly)

        for index in indexes:
            if index.isValid():
                pixmap = QtGui.QPixmap(self.data(index, Qt.UserRole))
                stream << pixmap

        mimeData.setData('image/x-tile-piece', encodedData)
        return mimeData


    def rowCount(self, parent):
        if parent.isValid():
            return 0
        else:
            return len(self.pixmaps)

    def supportedDragActionszzzzz(self):
        return Qt.CopyAction | Qt.MoveAction



#############################################################################################
###################### Python-based RGB4A3 decoding code from BRFNTify ######################


def RGB4A3Decode(tex, useAlpha=True):
    dest = QtGui.QImage(1024,256,QtGui.QImage.Format_ARGB32)
    dest.fill(Qt.transparent)
    
    i = 0
    for ytile in range(0, 256, 4):
        for xtile in range(0, 1024, 4):
            for ypixel in range(ytile, ytile + 4):
                for xpixel in range(xtile, xtile + 4):
                    
                    if(xpixel >= 1024 or ypixel >= 256):
                        continue
                    
                    newpixel = (tex[i] << 8) | tex[i+1]
                    
    
                    if(newpixel >= 0x8000): # Check if it's RGB555
                        red = ((newpixel >> 10) & 0x1F) * 255 / 0x1F
                        green = ((newpixel >> 5) & 0x1F) * 255 / 0x1F
                        blue = (newpixel & 0x1F) * 255 / 0x1F
                        alpha = 0xFF
    
                    else: # If not, it's RGB4A3
                        alpha = ((newpixel & 0x7000) >> 12) * 255 / 0x7
                        blue = ((newpixel & 0xF00) >> 8) * 255 / 0xF
                        green = ((newpixel & 0xF0) >> 4) * 255 / 0xF
                        red = (newpixel & 0xF) * 255 / 0xF

                    alpha, red, green, blue = int(alpha), int(red), int(green), int(blue)
                    if not useAlpha: alpha = 0xFF
    
                    argb = (blue) | (green << 8) | (red << 16) | (alpha << 24)
                    dest.setPixel(xpixel, ypixel, argb)
                    i += 2
    return dest


def RGB4A3Encode(tex):
    destBuffer = create_string_buffer(524288)

    shortstruct = struct.Struct('>H')
    offset = 0

    for ytile in range(0, 256, 4):
        for xtile in range(0, 1024, 4):
            for ypixel in range(ytile, ytile + 4):
                for xpixel in range(xtile, xtile + 4):
                    
                    if(xpixel >= 1024 or ypixel >= 256):
                        continue
                    
                    pixel = tex.pixel(xpixel, ypixel)
                    
                    a = pixel >> 24
                    r = (pixel >> 16) & 0xFF
                    g = (pixel >> 8) & 0xFF
                    b = pixel & 0xFF
                    
                    if a < 245: # RGB4A3
                        alpha = a/32
                        red = r/16
                        green = g/16
                        blue = b/16

                        rgbDAT = (blue) | (green << 4) | (red << 8) | (alpha << 12)
                
                    else: # RGB555
                        red = r/8
                        green = g/8
                        blue = b/8
                        
                        rgbDAT = (blue) | (green << 5) | (red << 10) | (0x8000) # 0rrrrrgggggbbbbb
                                                                                                            
                    shortstruct.pack_into(destBuffer, offset, rgbDAT)
                    offset += 2
                    
    return destBuffer.raw


#############################################################################################
############ Main Window Class. Takes care of menu functions and widget creation ############


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.tileImage = QtGui.QPixmap()
        self.collision = False
        self.alpha = True
        
        global Tileset
        Tileset = TilesetClass()

        self.name = ''

        self.setupMenus()
        self.setupWidgets()

        self.setuptile()

        self.newTileset()

        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed,
                QtWidgets.QSizePolicy.Fixed))
        self.setWindowTitle('Puzzle Next - Pa1_untitled')


    def setuptile(self):
        self.tileWidget.tiles.clear()
        self.model.clear()

        if self.alpha == True:
            for tile in Tileset.tiles:
                self.model.addPieces(tile.image)
        else:
            for tile in Tileset.tiles:
                self.model.addPieces(tile.noalpha)


    def newTileset(self):
        """Creates a new, blank tileset"""
        
        global Tileset
        Tileset.clear()
        Tileset = TilesetClass()
        
        EmptyPix = QtGui.QPixmap(24, 24)
        EmptyPix.fill(Qt.transparent)
        
        for i in range(256):
            Tileset.addTile(EmptyPix, EmptyPix)

        self.setuptile()
        self.setWindowTitle('Puzzle Next - Untitled')
        
        
    def openTileset(self):
        """Opens a Nintendo tileset arc and parses the heck out of it."""
        
        path = QtWidgets.QFileDialog.getOpenFileName(self, 'Open NSMBW Tileset', '',
            'Image Files (*.arc)')[0]
        if not path: return
                    
        self.setWindowTitle('Puzzle Next - ' + os.path.basename(path))
        Tileset.clear()

        self.internalname = path.split('/')[-1][:-4]
    
        file = open(path,'rb')
        data = file.read()
        file.close()
        
        datastr = data.decode('latin-1')
        arc = archive.U8.load(datastr)
        
        Image, behaviordata, objstrings, metadata = [None] * 4
        
        for key, value in arc.files:
            if value == None:
                pass
            if key.startswith('BG_tex/') and key.endswith('_tex.bin.LZ'):
                Image = bytes(arc[key], 'latin-1')
            if key.startswith('BG_chk/d_bgchk_') and key.endswith('.bin'):
                behaviordata = bytes(arc[key], 'latin-1')
            if key.startswith('BG_unt/'):
                if key.endswith('_hd.bin'):
                    metadata = bytes(arc[key], 'latin-1')
                elif key.endswith('.bin'):
                    objstrings = bytes(arc[key], 'latin-1')


        if (Image == None) or (behaviordata == None) or (objstrings == None) or (metadata == None):
            QtWidgets.QMessageBox.warning(None, 'Error', 
                'Error - the necessary files were not found.\n\nThis is not a valid tileset, sadly.',
                )
            return
        
        # Stolen from Reggie! Loads the Image Data.
        if HaveNSMBLib:
            tiledata = nsmblib.decompress11LZS(Image)
            argbdata = nsmblib.decodeTileset(tiledata)
            #rgbdata = nsmblib.decodeTilesetNoAlpha(tiledata)
            rgbdata = nsmblib.decodeTileset(tiledata)
            dest = QtGui.QImage(argbdata, 1024, 256, 4096, QtGui.QImage.Format_ARGB32_Premultiplied)
            noalphadest = QtGui.QImage(rgbdata, 1024, 256, 4096, QtGui.QImage.Format_ARGB32_Premultiplied)
        else:
            lz = lz77.LZS11()
            decomp = lz.Decompress11LZS(Image)
            dest = RGB4A3Decode(decomp)
            noalphadest = RGB4A3Decode(decomp, False)
        
        self.tileImage = QtGui.QPixmap.fromImage(dest)
        noalpha = QtGui.QPixmap.fromImage(noalphadest)
        
        # Loads Tile behaviors
                    
        behaviors = []
        for entry in range(256):
            behaviors.append(struct.unpack_from('>8B', behaviordata, entry*8))
        
        
        # Makes us some nice Tile Classes!
        Xoffset = 4
        Yoffset = 4
        for i in range(256):
            Tileset.addTile(self.tileImage.copy(Xoffset,Yoffset,24,24), noalpha.copy(Xoffset,Yoffset,24,24), behaviors[i])
            Xoffset += 32
            if Xoffset >= 1024:
                Xoffset = 4
                Yoffset += 32                    
        
        
        # Load Objects
        
        meta = []
        for i in range(int(len(metadata)/4)):
            meta.append(struct.unpack_from('>H2B', metadata, i * 4))                                    
            
        tilelist = [[]]
        upperslope = [0, 0]
        lowerslope = [0, 0]
        byte = 0
        
        for entry in meta:  
            offset = entry[0]
            byte = struct.unpack_from('>B', objstrings, offset)[0]
            row = 0
            
            while byte != 0xFF:

                if byte == 0xFE:
                    tilelist.append([])

                    if (upperslope[0] != 0) and (lowerslope[0] == 0):
                        upperslope[1] = upperslope[1] + 1
                        
                    if lowerslope[0] != 0:
                        lowerslope[1] = lowerslope[1] + 1

                    offset += 1
                    byte = struct.unpack_from('>B', objstrings, offset)[0]

                elif (byte & 0x80):

                    if upperslope[0] == 0:
                        upperslope[0] = byte
                    else:
                        lowerslope[0] = byte
                        
                    offset += 1
                    byte = struct.unpack_from('>B', objstrings, offset)[0]
                    
                else:
                    tilelist[len(tilelist)-1].append(struct.unpack_from('>3B', objstrings, offset))

                    offset += 3
                    byte = struct.unpack_from('>B', objstrings, offset)[0]

            tilelist.pop()

            if (upperslope[0] & 0x80) and (upperslope[0] & 0x2):
                for i in range(lowerslope[1]):
                    pop = tilelist.pop()
                    tilelist.insert(0, pop)

            Tileset.addObject(entry[2], entry[1], upperslope, lowerslope, tilelist)

            tilelist = [[]]
            upperslope = [0, 0]
            lowerslope = [0, 0]

        Tileset.slot = Tileset.objects[0].tiles[0][0][2] & 3
        self.tileWidget.tilesetType.setText('Pa{0}'.format(Tileset.slot))

        self.setuptile()
        SetupObjectModel(self.objmodel, Tileset.objects, Tileset.tiles)

        self.namePrefixCombo.setCurrentIndex(Tileset.slot)
        self.nameBox.setText(self.internalname)

        self.name = path


    def openImage(self):
        """Opens an image from a PNG file, and creates a new tileset from it."""

        path = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Image', '',
            'Image Files (*.png)')[0]
        if not path: return

        newImage = QtGui.QPixmap()
        self.tileImage = newImage

        if not newImage.load(path):
            QtWidgets.QMessageBox.warning(self, 'Open Image',
                    'The image file could not be loaded.',
                    QtWidgets.QMessageBox.Cancel)
            return

        if not newImage.width() == 384 and newImage.height() == 384:
            QtWidgets.QMessageBox.warning(self, 'Open Image',
                    'The image was not the proper dimensions.'
                    'Please resize the image to 384x384 pixels.',
                    QtWidgets.QMessageBox.Cancel)
            return

        x, y = 0, 0
        for i in range(256):
            Tileset.tiles[i].image = self.tileImage.copy(x * 24, y * 24, 24, 24)
            x += 1
            if x * 24 >= 384:
                y += 1
                x = 0

        self.setuptile()


    def saveImage(self):
            
        fn = QtWidgets.QFileDialog.getSaveFileName(self, 'Choose a new filename', '',
            '.png (*.png)')[0]
        if not fn: return
        
        tex = QtGui.QPixmap(384, 384)
        tex.fill(Qt.transparent)
        painter = QtGui.QPainter(tex)
        
        Xoffset = 0
        Yoffset = 0
        
        for tile in Tileset.tiles:
            painter.drawPixmap(Xoffset, Yoffset, tile.image)
            Xoffset += 24
            if Xoffset >= 384:
                Xoffset = 0
                Yoffset += 24
                        
        painter.end()

        tex.save(fn)
        
        
    def saveTileset(self):
        if self.name == '':
            self.saveTilesetAs()
            return
            
        
        outdata = self.saving(self.internalname)
        
        fn = self.name
        f = open(fn, 'wb')
        f.write(outdata)
        f.close()
                
        
    def saveTilesetAs(self):
        
        fn = QtWidgets.QFileDialog.getSaveFileName(self, 'Choose a new filename', '',
            '.arc (*.arc)')[0]
        if not fn: return

        self.name = fn
        self.setWindowTitle('Puzzle Next - ' + os.path.basename(str(fn)))
        
        outdata = self.saving(self.internalname)
        f = open(fn, 'wb')
        f.write(outdata)
        f.close()


    def saving(self, name):

        # Prepare tiles, objects, object metadata, and textures and stuff into buffers.

        textureBuffer = self.PackTexture()
        tileBuffer = self.PackTiles()
        objectBuffers = self.PackObjects()
        objectBuffer = objectBuffers[0]
        objectMetaBuffer = objectBuffers[1]
        
                
        # Make an arc and pack up the files!
        arc = archive.U8()
        arc['BG_tex'] = None
        arc['BG_tex/{0}_tex.bin.LZ'.format(name)] = textureBuffer

        arc['BG_chk'] = None
        arc['BG_chk/d_bgchk_{0}.bin'.format(name)] = tileBuffer

        arc['BG_unt'] = None
        arc['BG_unt/{0}.bin'.format(name)] = objectBuffer
        arc['BG_unt/{0}_hd.bin'.format(name)] = objectMetaBuffer
        
        return arc._dump()


    def PackTexture(self):

        tex = QtGui.QImage(1024, 256, QtGui.QImage.Format_ARGB32)
        tex.fill(Qt.transparent)
        painter = QtGui.QPainter(tex)
        
        Xoffset = 0
        Yoffset = 0

        for tile in Tileset.tiles:
            minitex = QtGui.QImage(32, 32, QtGui.QImage.Format_ARGB32)
            minitex.fill(Qt.transparent)
            minipainter = QtGui.QPainter(minitex)
            
            minipainter.drawPixmap(4, 4, tile.image)
            minipainter.end()
            
            # Read colors and DESTROY THEM (or copy them to the edges, w/e)
            for i in range(4,28):
                
                # Top Clamp
                color = minitex.pixel(i, 4)
                for p in range(0,4):
                    minitex.setPixel(i, p, color)
                
                # Left Clamp
                color = minitex.pixel(4, i)
                for p in range(0,4):
                    minitex.setPixel(p, i, color)
                
                # Right Clamp
                color = minitex.pixel(i, 27)
                for p in range(27,31):
                    minitex.setPixel(i, p, color)
                
                # Bottom Clamp
                color = minitex.pixel(27, i)
                for p in range(27,31):
                    minitex.setPixel(p, i, color)

            # UpperLeft Corner Clamp
            color = minitex.pixel(4, 4)
            for x in range(0,4):
                for y in range(0,4):
                    minitex.setPixel(x, y, color)

            # UpperRight Corner Clamp
            color = minitex.pixel(27, 4)
            for x in range(27,31):
                for y in range(0,4):
                    minitex.setPixel(x, y, color)

            # LowerLeft Corner Clamp
            color = minitex.pixel(4, 27)
            for x in range(0,4):
                for y in range(27,31):
                    minitex.setPixel(x, y, color)

            # LowerRight Corner Clamp
            color = minitex.pixel(27, 27)
            for x in range(27,31):
                for y in range(27,31):
                    minitex.setPixel(x, y, color)

                    
            painter.drawImage(Xoffset, Yoffset, minitex)
            
            Xoffset += 32
            
            if Xoffset >= 1024:
                Xoffset = 0
                Yoffset += 32
                                    
        painter.end()

        dest = RGB4A3Encode(tex)
        
        
        items = ('Very Slow Compression, Good Quality', 'Fast Compression, but the Image gets damaged')

        item, ok = QtWidgets.QInputDialog.getItem(self, 'Choose compression method',
                'Two methods of compression are available. Choose \n'
                'fast compression for rapid testing. Choose slow \n'
                'compression for releases. Bug Treeki to get the fast \n'
                'compression fixed!', items, 0, False)
        if ok and item == 'Very Slow Compression, Good Quality':
            lz = lz77.LZS11()

            progress = QtWidgets.QProgressDialog(self)
            progress.setCancelButton(None)
            progress.setMinimumDuration(0)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle('Puzzle')
            lz.SetProgressBar(progress)
            
            TexBuffer = (lz.Compress11LZS(dest))
            progress.setValue(progress.maximum()) # autodeletes it
        else:
            TexBuffer = nsmblib.compress11LZS(dest)
        
        return TexBuffer


    def PackTiles(self):
        offset = 0
        tilespack = struct.Struct('>8B')
        Tilebuffer = create_string_buffer(2048)
        for tile in Tileset.tiles:
            tilespack.pack_into(Tilebuffer, offset, tile.byte0, tile.byte1, tile.byte2, tile.byte3, tile.byte4, tile.byte5, tile.byte6, tile.byte7)
            offset += 8
                    
        return Tilebuffer.raw


    def PackObjects(self):
        objectStrings = []
        
        o = 0
        for object in Tileset.objects:
                 
                
            # Slopes
            if object.upperslope[0] != 0:
                
                # Reverse Slopes
                if object.upperslope[0] & 0x2:
                    a = struct.pack('>B', object.upperslope[0])
                    
                    if object.height == 1:
                        iterationsA = 0
                        iterationsB = 1
                    else:
                        iterationsA = object.upperslope[1]
                        iterationsB = object.lowerslope[1] + object.upperslope[1]
                        
                    for row in range(iterationsA, iterationsB):
                        for tile in object.tiles[row]:
                            a = a + struct.pack('>BBB', tile[0], tile[1], tile[2])
                        a = a + '\xfe'

                    if object.height > 1:
                        a = a + struct.pack('>B', object.lowerslope[0])
                    
                        for row in range(0, object.upperslope[1]):
                            for tile in object.tiles[row]:
                                a = a + struct.pack('>BBB', tile[0], tile[1], tile[2])
                            a = a + '\xfe'
                        
                    a = a + '\xff'
                    
                    objectStrings.append(a)
                    
                    
                # Regular Slopes   
                else:
                    a = struct.pack('>B', object.upperslope[0])
                    
                    for row in range(0, object.upperslope[1]):
                        for tile in object.tiles[row]:
                            a = a + struct.pack('>BBB', tile[0], tile[1], tile[2])
                        a = a + '\xfe'
                    
                    if object.height > 1:
                        a = a + struct.pack('>B', object.lowerslope[0])
                    
                        for row in range(object.upperslope[1], object.height):
                            for tile in object.tiles[row]:
                                a = a + struct.pack('>BBB', tile[0], tile[1], tile[2])
                            a = a + '\xfe'
                        
                    a = a + '\xff'
                    
                    objectStrings.append(a)
                    
                    
            # Not slopes!    
            else:
                a = ''
                
                for tilerow in object.tiles:
                    for tile in tilerow:
                        a = a + struct.pack('>BBB', tile[0], tile[1], tile[2])
                    
                    a = a + '\xfe'
                    
                a = a + '\xff'
                
                objectStrings.append(a)
            
            o += 1
            
        Objbuffer = ''
        Metabuffer = ''
        i = 0
        for a in objectStrings:
            Metabuffer = Metabuffer + struct.pack('>H2B', len(Objbuffer), Tileset.objects[i].width, Tileset.objects[i].height)
            Objbuffer = Objbuffer + a
            
            i += 1
        
        return (Objbuffer, Metabuffer)



    def setupMenus(self):

        def get(name):
            """
            Returns an icon
            """
            try:
                return QtGui.QIcon('MenuIcons/icon-' + name + '.png')
            except:
                return None

        fileMenu = self.menuBar().addMenu('&File')
        fileMenu.addAction(get('new'), 'New', self.newTileset, QtGui.QKeySequence.New)
        fileMenu.addAction(get('open'), 'Open...', self.openTileset, QtGui.QKeySequence.Open)
        fileMenu.addAction(get('import'), 'Import Image...', self.openImage, QtGui.QKeySequence('Ctrl+I'))
        fileMenu.addAction(get('export'), 'Export Image...', self.saveImage, QtGui.QKeySequence('Ctrl+E'))
        fileMenu.addAction(get('save'), 'Save', self.saveTileset, QtGui.QKeySequence.Save)
        fileMenu.addAction(get('saveas'), 'Save as...', self.saveTilesetAs, QtGui.QKeySequence('Ctrl+Shift+S'))
        fileMenu.addAction(get('exit'), 'Exit', self.close, QtGui.QKeySequence('Ctrl+Q'))

        viewMenu = self.menuBar().addMenu('&View')
        a = viewMenu.addAction('Overlay Collision', lambda: None, QtGui.QKeySequence('Ctrl+Shift+O'))
        a.setCheckable(True)
        a.toggled.connect(self.collisionOverlay)
        a = viewMenu.addAction('Show Alpha', lambda: None, QtGui.QKeySequence('Ctrl+Shift+A'))
        a.setCheckable(True)
        a.setChecked(True)
        a.toggled.connect(self.toggleAlpha)

        taskMenu = self.menuBar().addMenu('&Tasks')
        #taskMenu.addAction('Set Tileset Slot...', self.setSlot, QtGui.QKeySequence('Ctrl+T'))
        taskMenu.addAction('Clear Collision Data', Tileset.clearCollisions, QtGui.QKeySequence('Ctrl+Shift+Backspace'))
        taskMenu.addAction('Clear Object Data', Tileset.clearObjects, QtGui.QKeySequence('Ctrl+Alt+Backspace'))


    def setSlot(self, slotNum):
        """
        Sets the tileset slot
        """
        global Tileset
        Tileset.slot = slotNum
        self.tileWidget.tilesetType.setText('Pa' + str(slotNum))

        cobj = 0
        crow = 0
        ctile = 0
        for object in Tileset.objects:
            for row in object.tiles:
                for tile in row:
                    if tile != (0,0,0):
                        Tileset.objects[cobj].tiles[crow][ctile] = (tile[0], tile[1], (tile[2] & 0xFC) | slotNum)
                    if tile == (0,0,0) and ctile == 0:
                        Tileset.objects[cobj].tiles[crow][ctile] = (tile[0], tile[1], (tile[2] & 0xFC) | slotNum)
                    ctile += 1
                crow += 1
                ctile = 0
            cobj += 1
            crow = 0
            ctile = 0

    def collisionOverlay(self, enabled):
        """
        Collision overlay clicked
        """
        self.collision = enabled
        self.updateInfo(0, 0)


    def toggleAlpha(self, enabled):
        """
        Replace Alpha Image with non-Alpha images in model
        """
        self.alpha = enabled

        self.setuptile()
        

    def setupWidgets(self):
        frame = QtWidgets.QWidget()
        frameLayout = QtWidgets.QGridLayout(frame)

        # Displays the tiles
        self.tileDisplay = displayWidget()
        
        # Info Box for tile information
        self.infoDisplay = InfoBox(self)
        
        # Sets up the model for the tile pieces
        self.model = PiecesModel(self)
        self.tileDisplay.setModel(self.model)

        # Object List
        self.objectList = objectList()
        self.objmodel = QtGui.QStandardItemModel()
        SetupObjectModel(self.objmodel, Tileset.objects, Tileset.tiles)
        self.objectList.setModel(self.objmodel)

        # Creates the Tab Widget for behaviors and objects
        self.tabWidget = QtWidgets.QTabWidget()

        # First tab
        self.namePrefixCombo = QtWidgets.QComboBox()
        self.namePrefixCombo.addItems([
            'Pa0',
            'Pa1',
            'Pa2',
            'Pa3',
            ])
        self.namePrefixCombo.setCurrentIndex(1)
        self.namePrefixCombo.currentIndexChanged.connect(self.setSlot)
        self.nameBox = QtWidgets.QLineEdit('Pa1_untitled')
        tileSettingsLayout = QtWidgets.QFormLayout()
        tileSettingsLayout.addRow('Slot:', self.namePrefixCombo)
        tileSettingsLayout.addRow('Name:', self.nameBox)
        metaWidget = QtWidgets.QWidget()
        metaWidget.setLayout(tileSettingsLayout)

        # Second tab
        self.paletteWidget = paletteWidget(self)

        # Third tab
        self.container = QtWidgets.QWidget()
        self.tileWidget = tileOverlord()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.objectList)
        layout.addWidget(self.tileWidget)
        self.container.setLayout(layout)

        # Sets the Tabs
        self.tabWidget.addTab(metaWidget, 'Meta')
        self.tabWidget.addTab(self.paletteWidget, 'Collisions')
        self.tabWidget.addTab(self.container, 'Objects')

        # Connections do things!
        self.tileDisplay.clicked.connect(self.paintFormat)
        self.tileDisplay.mouseMoved.connect(self.updateInfo)
        self.objectList.clicked.connect(self.tileWidget.setObject)
        
        # Layout
        frameLayout.addWidget(self.tileDisplay, 0, 0)
        frameLayout.addWidget(self.infoDisplay, 1, 0)
        frameLayout.addWidget(self.tabWidget, 0, 1, 2, 1)
        self.setCentralWidget(frame)


    def updateInfo(self, x, y):
        """
        Handles mouse movement to point (x, y) on self.tileDisplay
        """
        index = [self.tileDisplay.indexAt(QtCore.QPoint(x, y))]
        tileIdx = index[0].row()
        if tileIdx == -1: tileIdx = None
        self.infoDisplay.updateInfo(tileIdx)


    def paintFormat(self, index):
        """
        Handles clicks on self.tileDisplay
        """
        if not self.tabWidget.currentIndex() == 1: return
    
        curTile = Tileset.tiles[index.row()]
        palette = self.paletteWidget

        newData = palette.currentData()
        curTile.byte0 = newData[0]
        curTile.byte1 = newData[1]
        curTile.byte2 = newData[2]
        curTile.byte3 = newData[3]
        curTile.byte4 = newData[4]
        curTile.byte5 = newData[5]
        curTile.byte6 = newData[6]
        curTile.byte7 = newData[7]

        self.updateInfo(0, 0)
        self.tileDisplay.update()



#############################################################################################
####################################### Main Function #######################################


def main():
    """
    Main function
    """
    global app, HexFont, window

    app = QtWidgets.QApplication(sys.argv)

    HexFont = QtGui.QFont('"Courier New", Courier, monospace')
    HexFont.setPointSize(12)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
    app.deleteLater()

if __name__ == '__main__': main()