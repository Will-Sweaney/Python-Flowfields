import pygame
import numpy as np
import noise
import math
import os
from random import randint

# colour presets, think of the colour values as ratios
# all 3 values must be 1 - 255
colours = {
    "red" : (20, 1, 1),
    "orange" : (20, 10, 1),
    "yellow" : (10, 10, 1),
    "green" : (1, 20, 1),
    "turquoise" : (1, 14, 20),
    "blue" : (1, 6, 24),
    "purple" : (8, 1, 16),
    "white" : (8, 8, 8),
}

# width and height of the display in px
targetWindowSize:int = 800

# number of initial particles
points:int = 1000

# how "dense" the noise is
noiseScale:float = 5

# size of each pixel
pixelScale:int = 2

# colour value of each particle. Combined when particle trails overlap
pixelColourRGB:tuple = colours['blue']

# how the surface affects the speed of each particle
# default for both is 1
friction:float = 0.1
acceleration:float = 1

# if the particle reaches the edge, mirror it to the other edge
# when set to False, the particle is destroyed
mirrorEdgesOnContact = True

# can fix gaps when friction or acceleration is low
interpolation = True

# take a screenshot of the flowfield when the window is closed
# screenshots are saved to ./results/
screenshotOnClose = True


##############################


pygame.init()

displayWidth = targetWindowSize // pixelScale
displayHeight = targetWindowSize // pixelScale

screen = pygame.display.set_mode((displayWidth * pixelScale, displayHeight * pixelScale))

pixelColourArray = np.zeros((displayHeight, displayWidth, 3), dtype=np.uint8)
particlePositions = np.empty((0, 4), dtype=np.float16)

pixelSurface = pygame.Surface((displayWidth, displayHeight))

running = True
clock = pygame.time.Clock()

for _ in range(points):
    xo = randint(0, displayWidth)
    yo = randint(0, displayHeight)

    particlePositions = np.vstack([particlePositions, (xo, yo, 0, 0)])

def saveScreenshot(folder="results"):
    os.makedirs(folder, exist_ok=True)

    parts = []

    for name, value in colours.items():
        if value == pixelColourRGB:
            parts.append(name)
            break
    if interpolation:
        parts.append("interpolation")
    if mirrorEdgesOnContact:
        parts.append("mirror")

    name = "-".join(parts)

    i = 0
    while os.path.exists(os.path.join(folder, f"{name}-{i}.png")):
        i += 1

    filename = os.path.join(folder, f"{name}-{i}.png")
    pygame.image.save(screen, filename)
    print(f"\nSaved image to {filename}")

def lerp(a, b, t):
    return a + (b - a) * t

def interpolate(x1, y1, x2, y2, steps):
    result = []
    for i in range(0, steps):
        t = i/steps
        x = lerp(x1, x2, t)
        y = lerp(y1, y2, t)
        result.append((x,y))
    return result

def closeWindow(timeToAdmire = 5):
    if screenshotOnClose:
        saveScreenshot()

    print()
    for second in range(timeToAdmire):
        print(f'\rClosing in {timeToAdmire - second}...', end='', flush=True)
        pygame.time.delay(1000)
    print('\r', end='', flush=True)
    pygame.quit()

def deleteParticle(index):
    global particlePositions
    particlePositions = np.delete(particlePositions, index, axis=0)

    percentage = int((points - len(particlePositions)) / points * 100) // 2
    progress = 'Cleaning up: [' + '=' * percentage + ' ' * (50 - percentage) + ']'
    print('\r' + progress, end='', flush=True)

def boundPositionToWindow(x, y, particleID):

    if not (0 <= x < displayWidth):
        if mirrorEdgesOnContact:
            x %= displayWidth
        else:
            deleteParticle(particleID)
            x = 0
    if not (0 <= y < displayHeight):
        if mirrorEdgesOnContact:
            y %= displayHeight
        else:
            deleteParticle(particleID)
            y = 0
    
    return x, y

def getNewParticlePosition(x, y, velX, velY, particleID):
    perlin = noise.snoise2(x / (displayWidth + 1) * noiseScale, y / (displayHeight + 1) * noiseScale)

    perlin = (perlin + 1) / 2
    rad = math.pi * 2 * perlin

    accelX = math.cos(rad) * acceleration
    accelY = math.sin(rad) * acceleration
    
    velX = (velX + accelX) / (friction + 1)
    velY = (velY + accelY) / (friction + 1)

    newX = x + velX
    newY = y + velY
    
    return newX, newY, velX, velY
        
def drawParticle(x, y, currentPos):
    x = int(x)
    y = int(y)

    currentPixel = pixelColourArray[y, x]
    newColor = np.clip(currentPixel + pixelColourRGB, 0, 255)

    if np.all(newColor == 255):
        deleteParticle(currentPos)
        return 1
    else:
        pixelColourArray[y, x] = newColor

    return 0

def drawLine(x1, y1, x2, y2, particleID):
    dx = abs(x1 - x2)
    dy = abs(y1 - y2)
    maxDistance = max(dx, dy)

    edgeMargin = (1 / friction) * acceleration

    if 1 <= maxDistance < min(displayWidth - edgeMargin, displayHeight - edgeMargin):
        lerpCount = math.ceil(maxDistance)
        lerpPositions = interpolate(x1, y1, x2, y2, lerpCount)
        for pos in lerpPositions:
            x3, y3 = boundPositionToWindow(pos[0], pos[1], particleID)
            if x3 + y3 == 0:
                break
            status = drawParticle(x3, y3, particleID)
            if status == 1:
                break

# main rendering loop
while running:
    # end process if window is closed
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            closeWindow(0)

    particlePositionLength = len(particlePositions)

    # stop the loop if all pixels are dead
    if particlePositionLength == 0:
        running = False
        
    currentParticle = 0
    
    # loop through each particle
    while currentParticle < particlePositionLength:

        # avoid sync issues by ensuring the length of the array
        if currentParticle >= len(particlePositions):
            break
        
        # retrieve the particle position and vector
        x1, y1, vx1, vy1 = particlePositions[currentParticle]

        # update the particle position and vector
        x2, y2, vx2, vy2 = getNewParticlePosition(x1, y1, vx1, vy1, currentParticle)

        # ensure the particle stays within the window
        x2, y2 = boundPositionToWindow(x2, y2, currentParticle)

        # when particles are not mirrored, they are killed when out of frame
        if x2 + y2 == 0:
            currentParticle += 1
            continue

        # save the particle position and vector
        particlePositions[currentParticle] = (x2, y2, vx2, vy2)

        # interpolate between points or draw a single pixel
        if interpolation != True:
            drawParticle(x2,y2, currentParticle)
        else:
            drawLine(x1, y1, x2, y2, currentParticle)

        # next particle
        currentParticle += 1

    # render colour array
    pygame.surfarray.blit_array(pixelSurface, pixelColourArray)

    # scale the surface based on pixelScale
    scaledSurface = pygame.transform.scale(pixelSurface, (displayWidth * pixelScale, displayHeight * pixelScale))
    screen.blit(scaledSurface, (0, 0))

    # render frame
    pygame.display.flip()

closeWindow()
