#! /usr/local/bin/python
#coding=UTF-8

from AppKit import NSSpeechSynthesizer, NSMutableString
import re
import string
import random
import Levenshtein
from operator import itemgetter
import twitter
import datetime
import time
import htmlentitydefs

################################################
#Important globals that need set up at the start
#https://developer.apple.com/library/mac/#documentation/UserExperience/Conceptual/SpeechSynthesisProgrammingGuide/Phonemes/Phonemes.html#//apple_ref/doc/uid/TP40004365-CH9-SW1
################################################
speechSynthesizer = NSSpeechSynthesizer.alloc().initWithVoice_("com.apple.speech.synthesis.voice.Bruce")
phonemeList = ["%", "@", "AE", "EY", "AO", "AX", "IY", "EH", "IH", "AY", "IX", "AA", "UW", "UH", "UX", "OW", "AW", "OY", "b", "C", "d", "D", "f", "g", "h", "J", "k", "l", "m", "n", "N", "p", "r", "s", "S", "t", "T", "v", "w", "y", "z", "Z"]
phonemeChars = "[^" + "".join(phonemeList) + "]" #regex referring to characters not in any phoneme
unVoiced = ["f", "k", "p", "s", "S", "C", "T", "w", "t"] #voiceless phonemes
voiced = ["b", "g", "J", "Z", "l", "m", "n", "N", "r", "y", "d", "D", "h", "v", "z", "AE", "EY", "AO", "AX", "IY", "EH", "IH", "AY", "IX", "AA", "UW", "UH", "UX", "OW", "AW", "OY"] #voiced phonemes
yourUserName = "REPLACE ME"

################################################
#TWITTER FUNCTIONS
################################################

#compose spoonerised tweet in reply
def makeTweetText(message, user, makeReply):
	global yourUserName

	#log the results - one log of all messages, one of messages + successful spoonerisms
	allMessages = open("allMessages.txt", "a")
	allMessages.write(message + "\n")
	allMessages.close()

	newMessage = unescape(makeSpoonerism(message))

	#replying, so include the actual username
	if (makeReply):
		atString = "@"
	else:
		atString = ""
		newMessage = string.replace(newMessage, "@", "") #remove @s so there are no mentions - don't want account suspended

	newMessage = atString + user + " " + newMessage #append original username (but don't make it a mention - suspension)
	
	#clean out mentions of yourself
	newMessage = re.sub(yourUserName, "", newMessage, flags=re.IGNORECASE) #remove mentions of yourself
	newMessage = " ".join(newMessage.split()) #remove double spaces
	
	#Log result
	collectedWorks = open("successfulSpoonerisms.txt", "a")
	collectedWorks.write(newMessage + "\t" + message + "\n")
	collectedWorks.close()

	return newMessage

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

################################################
#PHONETIC SPOONERISM FUNCTIONS
################################################

#turn a word into a string of phonemes - important to split the message into words first
def getPhonemes(word):
	global speechSynthesizer
	global phonemeChars
	
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
		phonemeList = [x.strip() for x in phonemeList] #remove newline charcters
		dictionary[textWord] = phonemeList #add to the dictionary
	
	print("Loaded dictionary from " + inputFile)
	return dictionary

#find the first vowel in a word
def findVowel(phonemeList):
	firstVowel = -1
	for i in range(1, len(phonemeList)):
		if len(phonemeList[i]) == 2:
			firstVowel = i
			break
	
	return firstVowel

#spoonerise! phonetically
def phoneticSpoonerise(phonemes1, phonemes2):

	#find the vowels
	vowel1 = findVowel(phonemes1)
	vowel2 = findVowel(phonemes2)

	if vowel1 == -1 or vowel2 == -1:
		raise Exception("No vowel to spoonerise with")

	#try all possible combos of spooning up until the vowel
	combos = []
	for v1 in range(1, vowel1 + 1):
		for v2 in range(1, vowel2 + 1):
			start1 = phonemes1[0:v1]
			end1 = phonemes1[v1:len(phonemes1)]
			start2 = phonemes2[0:v2]
			end2 = phonemes2[v2:len(phonemes2)]

			newWord1 = start2 + end1
			newWord2 = start1 + end2

			if newWord1 != phonemes1 and newWord2 != phonemes2:
				combos.append((newWord1, newWord2))

	return combos

#DO NOT USE THIS ONE. IT WILL TAKE 35 YEARS!
#check dictionary for all spellings
def findSpoonerisms(outputFile):
	global dictionary
	global dictValues	
	outputF = open(outputFile, "w+")

	#keep track of progress
	count = 0
	total = len(dictionary) * (len(dictionary) - 1)

	#test every possible combo from the dictionary
	for k1, v1 in dictionary.iteritems():
		for k2, v2 in dictionary.iteritems():
			if v2 != v1:
				print(str(count) + " of " + str(total) + ": " + k1.strip() + "/" + k2.strip()) #report progress
				count = count + 1
				try:
					spoonerisms = phoneticSpoonerise(v1, v2) #try spoonerising
					for combo in spoonerisms:
						if combo[0] in dictValues and combo[1] in dictValues: #if resulting pairs are real words
							outputF.write(k1.strip() + "/" + k2.strip() + "\n") #save to outputfile
				except:
					pass

	outputF.close()

#Actually do the work - spoonerises message phonetically
def phoneticSpooner(message):
	global dictionary

	#split the message into words
	message = message.strip().lower()
	words = message.split(" ")
	possibleSpoons = [] #use for storing results
	actualSpoons = []

	#try every possible combo of words from the message
	for word1 in words:
		for word2 in words[words.index(word1):]:

			split1 = splitPunctuation(word1)
			realWord1 = split1[0]
			startPunct1 = split1[1]
			endPunct1 = split1[2]

			split2 = splitPunctuation(word2)
			realWord2 = split2[0]
			startPunct2 = split2[1]
			endPunct2 = split2[2]

			if realWord1 != realWord2: #can't self-spoonerise
				try:
					phonemes1 = lookupPhonemes(realWord1)
					phonemes2 = lookupPhonemes(realWord2)	
		
					spoonerisms = phoneticSpoonerise(phonemes1, phonemes2) #can you spoonerise the two words -> find the sounds for each and swap?
					for spoons in spoonerisms:
						if len(spoons) != 0: #input words won't spoonerise if they have no vowels, etc	
							result = ((spoons[0], words.index(word1), startPunct1, endPunct1), (spoons[1], words.index(word2), startPunct2, endPunct2))
							possibleSpoons.append(result)
				except:
					pass

	#see if each possible set of spoonerisms gives actual dictionary words
	for combo in possibleSpoons:
		try: 
			newMessage = list(words) #make a copy of the original message

			posWord1 = combo[0][1] #which word in original message to swap?
			oldWord1 = newMessage[posWord1] #what was the old word
			newWord1 = findWord(combo[0][0], oldWord1) #look up in dictionary
			newWord1 = combo[0][2] + newWord1 + combo[0][3] #and add on the punctuation at the start and end
			newMessage[posWord1] = newWord1 #swap it for old word

			posWord2 = combo[1][1]
			oldWord2 = newMessage[posWord2]
			newWord2 = findWord(combo[1][0], oldWord2)
			newWord2 = combo[1][2] + newWord2 + combo[1][3] 
			newMessage[posWord2] = newWord2

			actualSpoons.append(" ".join(newMessage).capitalize()) #add it to the list of valid answers
		except:
			pass

	#no results - return none
	if len(actualSpoons) == 0:
		return None

	#if more than one result, will use a random one
	if len(actualSpoons) > 1:
		random.shuffle(actualSpoons)

	return actualSpoons[0]

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

#match phonemes back to a word
def findWord(phonemes, oldWord):
	global dictionary
	global homophoneList
	global voiced
	global unVoiced
	word = ""

	#go down the dictionary until you find matching phonemes
	for k, v in dictionary.iteritems():
		if v == phonemes:
			word = k
			break

	#if we know it's a homophone, need to see if it's the best one. if it's unique, then we're done
	if word in homophoneList:
		choices = homophones[word] #possible answers
		matches = [] #store results
		for w in choices:
			matches.append([w, Levenshtein.distance(w, oldWord)]) #see how close each possible new word is to the original
		matches = sorted(matches, key=itemgetter(1)) #pick the closest match
		word = matches[0][0]
	
	if len(word) == 0:
		raise Exception("No matching word in the dictionary")

	return word

#find homophones for each word
def makeHomophones(outputFile1, outputFile2):
	global dictionary
	global dictValues
	outputF = open(outputFile1, "w+")
	outputG = open(outputFile2, "w+")

	#work out which phonemes occur more than once
	uniqueHomophones = set(dictValues) #only deal with each one once
	homophonesPhonemes = set()
	count = 0
	for phoneme in uniqueHomophones: #go through all the homophones we have
		print(str(count) + " of " + str(len(uniqueHomophones)) + " " + ":".join(phoneme)) #report progress
		count = count + 1
		if dictValues.count(phoneme) > 1:
			homophonesPhonemes.add(phoneme) #add to set for processing below
			outputF.write(":".join(phoneme) + "\n") #save an intermediate step to speed up future goes
	outputF.close()

	#for the repeated phonemes, work out which words they have
	phonCount = 0
	for phoneme in homophonesPhonemes: #go through all the relevant phonemes
		phonemeSet = set()
		for k, v in dictionary.iteritems(): #see which words match them in the dictionary
			if v == phoneme:
				phonemeSet.add(k) #get all the relevant results
		result = "/".join(phonemeSet) #join them into a string
		print(str(phonCount) + " of " + str(len(homophonesPhonemes)) + " " + result) #report progress
		outputG.write(result + "\n") #store result for the morning
	
	outputG.close()

#read back a list of homophones
def readHomophones(inputFile):
	inputF = open(inputFile, "r")
	homophoneDict = {}

	for line in inputF:
		text = line.strip()
		words = text.split("/")
		for word in words:
			homophoneDict[word] = words

	print("Loaded homophones from " + inputFile)
	return homophoneDict

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

################################################
#LEXICAL SPOONERISM FUNCTIONS
################################################

#rewrite the message with spoonerised words
def lexicalSpooner(message):
	message = message.strip() #clean up input
	
	finalWords = lexicalFindWords(message) #find the words to use
	spoonerised = lexicalSpoonerise(finalWords[0][0], finalWords[1][0]) #spoonerise the longest two words

	splitMessage = message.split(" ") #split the message into its component parts

	#replace the old words with the spoonerised versions
	splitMessage[finalWords[0][1]] = spoonerised[0]
	splitMessage[finalWords[1][1]] = spoonerised[1]

	#put it all together into one string again
	newMessage = " ".join(splitMessage)
	newMessage = newMessage.capitalize()

	return newMessage

#find the longest two words in a message
def lexicalFindWords(message):
	message = message.strip() #clean up input
	allWords = message.split(" ")
	goodWords = []

	#make a new list, with just the actual words - strip out hashtags and usernames
	for word in allWords:
		if re.match("[A-Za-z,\.;:\?!]+$", word):
			goodWords.append(word)
		
	#sort it so longest words are first
	goodWords = sorted(goodWords, key=len, reverse=True)

	#return the longest two words, plus where they come in the original message
	finalWords = [ (word.lower(), allWords.index(word)) for word in goodWords if lexicalFindVowel(word) != -1]
	
	#need at least two words for it to work!
	if len(finalWords) < 2:
		raise RuntimeError("Message contains fewer than two useful words.")

	return finalWords

#swap the two words around
def lexicalSpoonerise(word1, word2):
	word1 = word1.strip() #tidy up the inputs
	word2 = word2.strip()

	split1 = lexicalWordSplit(word1)
	split2 = lexicalWordSplit(word2)

	#it's boring if the words started the same way!
	if (split1[0] == split2[0]):
		raise RuntimeError("Both words started the same, so no effect by spoonerising them")

	return [split2[0] + split1[1], split1[0] + split2[1]]

#split a word in two
def lexicalWordSplit(word):
	vowel = findVowel(word)
	return [word[0: vowel], word[vowel: len(word)]]

#find the first vowel in the word
def lexicalFindVowel(word):
	vowels = ['a', 'e', 'i', 'o', 'u'] #what are the vowels	
	vowelPositions = [ (vowel, word.find(vowel)) for vowel in vowels ] #make a list of tuples (vowel, position)
	vowelPositions = sorted(vowelPositions, key=itemgetter(1)) #sort the list
	
	firstVowel = -1 #default value
	for x in vowelPositions:
		if x[1] > 0:
			firstVowel = x[1]
			break

	return firstVowel


################################################
#CONTROL FUNCTION
################################################

def makeSpoonerism(message):
	spoonerism = phoneticSpooner(message)

	if spoonerism == None:
		spoonerism = lexicalSpooner(message)		

	return spoonerism

################################################
#ACTUALLY USE THE FUNCTIONS!
################################################

#PREPARE DATA FILES - FOR GETTING UP AND RUNNING
#makeDictionary("enable2k-contractions.txt", "wordPhoneme.txt") #words then phonemes in result
#makeHomophones("homophonemes.txt", "homophonewords.txt")

#READ BACK PRE-PREPARED DATA FILES
dictionary = readDictionary("phonemeDictionary.txt") #read back the phonetic dictionary
dictValues = dictionary.values()
homophones = readHomophones("homophonewords.txt")
homophoneList = homophones.keys()

#important global variables for looping
sinceID = getYourLastMessage(authenticate()) + 1 #should probably default to your last message sent in all cases
loopCount = 0

#Main loop
while True:
	print("")
	now = datetime.datetime.now()
	timestring = now.strftime("%Y-%m-%d %H:%M:%S") + " (UK)"
	descriptionString = "Tweet at me to get a spoonerised reply if I'm up and running. Last update: " + timestring + ". Photo: http://t.co/zXrADwk6"
	print("Starting loop " + str(loopCount) + " at " + timestring)
	print("Starting from message " + str(sinceID))
	twitterInstance = authenticate()
	twitterInstance.account.update_profile(description=descriptionString)
	print("Profile updated")	
	makeReplies()
	loopCount = loopCount + 1
	print("Loop finished")
	time.sleep(60)