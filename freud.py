#! /usr/local/bin/python
#coding=UTF-8

import re
from operator import itemgetter
import random
import htmlentitydefs
import string
import twitter
import datetime
import time

#Phoneme lists for usefulness later
phonemeList = ["%", "@", "AE", "EY", "AO", "AX", "IY", "EH", "IH", "AY", "IX", "AA", "UW", "UH", "UX", "OW", "AW", "OY", "b", "C", "d", "D", "f", "g", "h", "J", "k", "l", "m", "n", "N", "p", "r", "s", "S", "t", "T", "v", "w", "y", "z", "Z"]
phonemeChars = "[^" + "".join(phonemeList) + "]" #regex referring to characters not in any phoneme
unVoiced = ["f", "k", "p", "s", "S", "C", "T", "w", "t"] #voiceless phonemes
voiced = ["b", "g", "J", "Z", "l", "m", "n", "N", "r", "y", "d", "D", "h", "v", "z", "AE", "EY", "AO", "AX", "IY", "EH", "IH", "AY", "IX", "AA", "UW", "UH", "UX", "OW", "AW", "OY"] #voiced phonemes
yourUserName = "REPLACE ME"

############################################################
# Used to pre-process data files
############################################################

###1 Crawled http://www.noswearing.com for list of swear words

#parse crawl data (after a couple of modifications
def parseCrawl(inputFile, outputFile):
	newList = []
	crawlData = open(inputFile, "r")
	swearFile = open(outputFile, "w")
	for line in crawlData:
		line = line.replace("{\"word\": [", "")
		line = line.replace("\"More Slang Translators:\"]}", "")
		words = line.split(",")
		for word in words:
			word = word.strip()
			word = word.replace("\"", "")
			if len(word) > 0:
				swearFile.write(word + "\n")

#clean up results of webcrawl
def crawlClean(list):
	global newList
	for item in list:
		if isinstance(item, str):
			if item != "word" and item != "More Slang Translators:":
				newList.append(item)
		else:
			crawlClean(item)

###2 Make phonemic dictionary of those words

#turn a word into a string of phonemes - important to split the message into words first
def getPhonemes(word):
	from AppKit import NSSpeechSynthesizer, NSMutableString
	global phonemeChars
	
	speechSynthesizer = NSSpeechSynthesizer.alloc().initWithVoice_("com.apple.speech.synthesis.voice.Bruce")

	phonemes = speechSynthesizer.phonemesFromText_(word) #input message into synthesizer
	phonemes = re.sub(phonemeChars, "", phonemes) #get rid of non-phoneme information
	return phonemes

#function to split a word into component phonemes - returns a list
def splitWord(word):
	global phonemeList
	phonemes = []

	#make a new string from the 
	for i in range(len(word)):
		foundChar = False
		for phoneme in phonemeList:
			if not foundChar:
				if word[i] == phoneme:
					foundChar = True
					phonemes.append(word[i])
					break
				if i < (len(word) - 1):
					if (word[i] + word[i + 1]) == phoneme:
						foundChar = True
						phonemes.append(word[i] + word[i + 1])
						i = i + 1
						break

	return phonemes

#make a dictionary!
def makeDictionary(inputFile, outputFile):
	inputF = open(inputFile, "r")
	outputF = open(outputFile, "w+")

	for line in inputF:
		text = line.strip()
		phonemes = splitWord(getPhonemes(text))
		outputString = text + "/" + ":".join(phonemes)
		outputF.write(outputString + "\n")
		print(outputString)

	inputF.close()
	outputF.close()

#read a dictionary back from disk
def readDictionary(inputFile):
	inputF = open(inputFile, "r")
	dictionary = {}

	#parse the input
	for line in inputF:
		firstSplit = line.split("/") #actual word is after the slash
		textWord = firstSplit[0].strip()
		if len(textWord) == 0:
			break
		phonemeList = firstSplit[1].split(":") #split gives a list of phonemes - need it to be a tuple to be a dictionary key
		phonemeList = [str(x).strip() for x in phonemeList] #remove newline charcters
		dictionary[textWord] = phonemeList #add to the dictionary
	
	print("Loaded dictionary from " + inputFile)
	return dictionary

############################################################
# Do stuff with given input
############################################################

#split off punctuation from the end of a word
def splitPunctuation(inputW):
	#see if punctuation is at the start or end of the input
	start = re.search("^[!\?¡¿\.,;:\\/\(\)\[\]\{\}\"\']+", inputW) #'
	if start == None:
		start = 0
	else:
		start = start.end()

	ending = re.search("[!\?¡¿\.,;:\\/\(\)\[\]\{\}\"\']+$", inputW) #'
	if ending == None:
		ending = len(inputW)
	else:
		ending = ending.start()

	#split the input according to results
	startWord = inputW[:start]
	realWord = inputW[start:ending]
	endWord = inputW[ending:]

	return [realWord, startWord, endWord]

#find phonemes in the dictionary, check for ending in apostrophes
def lookupPhonemes(textWord):
	lookupWord = textWord
	ending = textWord[len(textWord) - 2:]

	#get the root word's phonemes, then add the correct ending	
	if ending == "'s": #'
		lookupWord = textWord[:len(textWord) - 2]
		phonemes = lookupPhonemes(lookupWord)

		#add proper end phoneme
		schwaList = ("s", "z", "J")
		endPhoneme = phonemes[len(phonemes) - 1]
		if endPhoneme in schwaList:
			phonemes.extend(["IX", "z"])
		elif endPhoneme in voiced:
			phonemes.append("z")
		elif endPhoneme in unVoiced:
			phonemes.append("s")

	#nothing special so look it up
	else:
		phonemes = list(dictionary[textWord])

	return phonemes

#choose a possible slip to be the actual result
def chooseSlip(slipList):
	lowestPhonemeDistance = min(slipList, key=itemgetter(2, 3))[2] #find the lowest edit distance
	lowestLexicalDistance = min(slipList, key=itemgetter(2, 3))[3] #find lowest spelling distance of closest sound match
	closestMatches = [item for item in slipList if item[2] == lowestPhonemeDistance and item[3] == lowestLexicalDistance] #extract subset with 
	
	#if one result, return it
	if (len(closestMatches) == 1):
		return closestMatches[0]

	#otherwise pick at random
	else:
		random.shuffle(closestMatches)
		return closestMatches[0]

#rewrite message with the slip in place
def freudianSlip(message):
	global dictionary
	global swearDictionary
	global swearHomophones

	try:
		message = message.strip() #clean input
		words = message.split(" ")
		wordList = [word for word in words if len(word) > 3] #only want to bother with real words - no hashtags or usernames

		possibleSlips = []
		for word in wordList:
			try:
				splitupWord = splitPunctuation(word)
				if re.match("[^#@]", splitupWord[0]):
					index = words.index(word) #what position in the original are we dealing with
					phonemes = lookupPhonemes(splitupWord[0]) #what does the word sound like?
					for k,v in swearDictionary.iteritems(): #try it against each swear word
						phonemeDistance = levenshteinDistance(phonemes, v) #how similar does your word sound like to the swear word
						lexicalDistance = levenshteinDistance(splitupWord[0], k)
						possibleSlips.append((k, index, phonemeDistance, lexicalDistance, splitupWord[1], splitupWord[2])) #add to the list
			except:
				pass

		slipWord = chooseSlip(possibleSlips)
		words[slipWord[1]] = slipWord[4] + slipWord[0] + slipWord[5] #replace word with swear
		newMessage = " ".join(words) #recombine it
		return newMessage
	except:
		pass

#Calculate edit distance between two lists (ie. can use it for phoneme lists as well as for strings)
#http://hetland.org/coding/python/levenshtein.py
def levenshteinDistance(a,b):
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n
        
    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)
            
    return current[n]

############################################################
# Twitter bits
############################################################

#authenticate for twitter
def authenticate():
	token = "REPLACE ME" #token api key
	token_key = "REPLACE ME" #token secret
	con_sec = "REPLACE ME" #consumer api key
	con_sec_key = "REPLACE ME" #consumer secret
	my_auth = twitter.OAuth(token, token_key, con_sec, con_sec_key)
	twit = twitter.Twitter(auth=my_auth)

	print("Authentication successful")
	return twit

#Post the new message
def postTweet(twit, tweetText, user, tweetID=-1):
	#post the message and follow the original tweeter
	if (tweetID == -1):
		twit.statuses.update(status=tweetText)
	else:
		twit.statuses.update(status=tweetText, in_reply_to_status_id=tweetID)
	#twit.friendships.create(screen_name=user) #follow original poster

#start from the last message you sent
def getYourLastMessage(twit):
	global YourUserName
	global sinceID
	myMessages = twit.statuses.user_timeline(screen_name=YourUserName, count=1)
	return int(myMessages[0]["id"])

#reply to messages
def makeReplies():
	global twitterInstance
	mentions = getMessages(twitterInstance)

	#make reply
	for tweet in range(0, len(mentions)):
		print("Attempting to make reply " + str(tweet) + " of " + str(len(mentions) - 1))
		try:
			oldID = mentions[tweet]["id"]
			oldMessage = str(mentions[tweet]["text"])
			oldUser = mentions[tweet]["user"]["screen_name"]
			newMessage = makeTweetText(oldMessage, oldUser, True)
			print("Formed message " + str(tweet) + ": " + newMessage)
			postTweet(twitterInstance, newMessage, oldUser, oldID)
			print("Posted message " + str(tweet))
		except:
			print("Failed to post message " + str(tweet))

def getMessages(twit):
	global sinceID
	mentions = twit.statuses.mentions_timeline(include_rts=0, since_id=sinceID)
	
	#update the starting point for next time
	for i in range(0, len(mentions)):
		thisID = int(mentions[i]["id"])
		if thisID > sinceID:
			sinceID = thisID

	#give you the list of mentions to work with
	return mentions

#compose freudian slip tweet in reply
def makeTweetText(message, user, makeReply):
	global yourUserName

	#log the results - one log of all messages, one of messages + successful results
	allMessages = open("allMessages.txt", "a")
	allMessages.write(message + "\n")
	allMessages.close()

	newMessage = unescape(freudianSlip(message))

	#replying, so include the actual username
	if (makeReply):
		atString = "@"
	else:
		atString = ""
		newMessage = string.replace(newMessage, "@", "") #remove @s so there are no mentions - don't want account suspended

	newMessage = atString + user + " " + newMessage #append original username (but don't make it a mention - suspension)
	
	#clean out mentions of yourself
	newMessage = re.sub(YourUserName, "", newMessage, flags=re.IGNORECASE) #remove mentions of yourself
	newMessage = " ".join(newMessage.split()).capitalize() #remove double spaces and capitalise
	
	#Log result
	collectedWorks = open("successfulSlips.txt", "a")
	collectedWorks.write(newMessage + "\t" + message + "\n")
	collectedWorks.close()

	return newMessage

def unescape(text):
	#from http://effbot.org/zone/re-sub.htm#unescape-html
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

############################################################
# Actually do stuff!
############################################################

dictionary = readDictionary("phonemeDictionary.txt")
swearDictionary = readDictionary("swearDictionary.txt")

#important global variables for looping
sinceID = getYourLastMessage(authenticate()) + 1 #should probably default to your last message sent in all cases
loopCount = 0

#Main loop
while True:
	try:
		print("")
		now = datetime.datetime.now()
		timestring = now.strftime("%Y-%m-%d %H:%M:%S") + " (PT)"

		descriptionString = "Tweet at me and I'll let you know what you're really thinking about. (Warning: rude). Last update: " + timestring + "."
		print("Starting loop " + str(loopCount) + " at " + timestring)
		print("Starting from message " + str(sinceID))
		twitterInstance = authenticate()
		twitterInstance.account.update_profile(description=descriptionString)
		print("Profile updated")	
		makeReplies()
		loopCount = loopCount + 1
		print("Loop finished")
	except:
		print("Loop " + str(loopCount) + " aborted")
	time.sleep(60)