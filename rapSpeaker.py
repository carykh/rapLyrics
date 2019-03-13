import samplerate
from gtts import gTTS
from scipy.io import wavfile
import numpy as np

from audiotsm import phasevocoder
from audiotsm.io.wav import WavReader, WavWriter
from pydub import AudioSegment
import pydub
import librosa
import soundfile as sf

print("starting!")

# input name, output name, song length (sec), tempo (sec per beats), delay before first beat, backtrack desired volume, spoken speed, have echo, line-range start, line-range end

PARAMS = [
["madeToMake.mp3","trial3.wav",185,0.42855208,13.89,0.2,0.6666666,True,0,75],
["OZsound-Sadness.mp3","songSadness.wav",228,0.479975,7.75,0.141,0.92,False,76,142],
["freeRapInstrumentalGetLost.mp3","songGetLost.wav",179,0.54543,17.49,0.17,0.7,True,606,653]]

PARAM_CHOICE = 0

SAMPLE_RATE = 44100
LOW_FACTOR = 1.42

SONG_LENGTH = PARAMS[PARAM_CHOICE][2]
MASTER_LENGTH = SAMPLE_RATE*SONG_LENGTH
BACKING_TRACK_VOLUME = PARAMS[PARAM_CHOICE][5]
WAITING_TIME = SAMPLE_RATE*PARAMS[PARAM_CHOICE][4]
SPEED_UP = PARAMS[PARAM_CHOICE][6]
HAVE_ECHO = PARAMS[PARAM_CHOICE][7]

sound = AudioSegment.from_mp3(PARAMS[PARAM_CHOICE][0])
sound.export("backingTrack.wav", format="wav")
_, backingTrack = wavfile.read("backingTrack.wav")
lowRegister = False

masterTrack = np.zeros((MASTER_LENGTH))
#MASK = 1+1.4*np.clip((np.arange(0,MASTER_LENGTH)-86.5*SAMPLE_RATE)/SAMPLE_RATE,0,1)  # very optional. Definitely don't need it : it just loudens everything from 1:26.5 onward.
masterTrack += backingTrack[0:MASTER_LENGTH,0]*BACKING_TRACK_VOLUME  #*MASK
beatOn = 0

SNAP_TIME = SAMPLE_RATE*PARAMS[PARAM_CHOICE][3]

linesFile = open("ROOF_no_3000.txt")
lines = linesFile.read().split("\n")[PARAMS[PARAM_CHOICE][8]:PARAMS[PARAM_CHOICE][9]]

def getFirstLoudPart(d):
    THRESHOLD = 0.2
    for i in range(len(d)):
        if(abs(d[i]) > THRESHOLD):
            return i

def getLastLoudPart(d):
    THRESHOLD = 0.07
    LAST_SYLLABLE_LENGTH = SAMPLE_RATE*0.21
    for i in range(len(d)-1,0,-1):
        if(abs(d[i]) > THRESHOLD):
            return i-LAST_SYLLABLE_LENGTH

def sanitize(line):
    return line.replace("nigger","ninja").replace("nigga","ninja")

def getStretchedData(low, sf):
    s = "placeholder.wav"
    playSpeed = 1/sf
    if low:
        s = "lowPlaceholder.wav"
        playSpeed *= LOW_FACTOR
    with WavReader(s) as reader:
        with WavWriter("stretchholder.wav", reader.channels, reader.samplerate) as writer:
            tsm = phasevocoder(reader.channels, speed=playSpeed)
            tsm.run(reader, writer)
    _, s = wavfile.read("stretchholder.wav")
    d = np.zeros(s.shape)
    if low:
        d += s
    else:
        d += s*0.81
    return d

def doFileStuff(line,isSlow):
    myobj = gTTS(text=line, lang='en', slow=isSlow) 
    myobj.save("placeholder.mp3")
    
    y, sr = librosa.load("placeholder.mp3")
    data = librosa.resample(y, sr, SAMPLE_RATE)
    librosa.output.write_wav('placeholder.wav', data, SAMPLE_RATE)
    d, sr = sf.read('placeholder.wav')
    sf.write('placeholder.wav', d, sr)

    y, sr = librosa.load("placeholder.mp3")
    lowData = librosa.resample(y, sr, SAMPLE_RATE*LOW_FACTOR)
    librosa.output.write_wav('lowPlaceholder.wav', lowData, SAMPLE_RATE)
    d, sr = sf.read('lowPlaceholder.wav')
    sf.write('lowPlaceholder.wav', d, sr)

    return data

i = 0
lastEchoData = np.zeros((1))
lastBeatOn = 0
for line in lines:
    i += 1
    if len(line) == 0:
        continue
    
    shouldChangeSinger = False
    if line[0] == "[":
        lowRegister = (not lowRegister)

    line = sanitize(line)

    data = doFileStuff(line,False)

    firstLoudPart = getFirstLoudPart(data)
    lastLoudPart = max(getLastLoudPart(data),firstLoudPart+SNAP_TIME)
    loudLength = lastLoudPart-firstLoudPart
    snappedLength = round(SPEED_UP*loudLength/SNAP_TIME)*SNAP_TIME
    if snappedLength <= 0:
        snappedLength = SNAP_TIME
    beatsUsed = int(round(snappedLength/SNAP_TIME))
    scalingFactor = snappedLength/loudLength

    print(scalingFactor)
    if scalingFactor >= 0.9: # uh-oh, this a stretch: quality isn't as good. Get the slow version.
        data = doFileStuff(line,True)

        firstLoudPart = getFirstLoudPart(data)
        beatsUsed = int(round(snappedLength/SNAP_TIME))
        lastLoudPart = max(getLastLoudPart(data),firstLoudPart+SNAP_TIME)
        loudLength = lastLoudPart-firstLoudPart
        scalingFactor = snappedLength/loudLength
        print("new: "+str(scalingFactor))

    stretchedData = getStretchedData(lowRegister, scalingFactor)

    nextBeatOn = beatOn+beatsUsed+1
    jumpGap = 0
    if (beatOn//16) != (nextBeatOn//16) and (beatOn+beatsUsed)%16 != 0 and nextBeatOn%16 != 0:
        jumpGap = (nextBeatOn//16)*16-beatOn
        beatOn = (nextBeatOn//16)*16
        nextBeatOn = beatOn+beatsUsed+1
    print("uhh?  "+str(beatOn))

    if jumpGap >= 1 and HAVE_ECHO:
        echoEdge = min(jumpGap,1)
        echoStart = int((lastBeatOn+echoEdge)*SNAP_TIME-firstLoudPart*scalingFactor+WAITING_TIME)
        echoEnd = echoStart+len(lastEchoData)

        fadeStart = end-SNAP_TIME*2
        fadeMask = np.clip((np.arange(echoStart,echoEnd)-fadeStart)/SNAP_TIME*3-2,0,1)
        masterTrack[echoStart:echoEnd] += lastEchoData*fadeMask*0.8

    lastEchoData = getStretchedData(not lowRegister, scalingFactor)

    start = int(beatOn*SNAP_TIME-firstLoudPart*scalingFactor+WAITING_TIME)
    end = start+len(stretchedData)
    masterTrack[start:end] += stretchedData*0.8

    lastBeatOn = beatOn
    beatOn = nextBeatOn
    
    print(str(i)+": "+line+",   "+str(beatOn*SNAP_TIME/SAMPLE_RATE/SONG_LENGTH))
    
    '''charAt = 0
    safeLine = line.upper()
    word = ""
    wordList = []
    for c in safeLine:
        if (ord(c) >= ord('A') and ord(c) <= ord('Z')) or c == '\'':
            word += c
        else:
            wordList.append(word)
            word = ""
    wordList.append(word)'''

extreme = max(np.amax(masterTrack),-np.amin(masterTrack))
masterTrack = masterTrack/extreme
wavfile.write(PARAMS[PARAM_CHOICE][1],SAMPLE_RATE,masterTrack)
