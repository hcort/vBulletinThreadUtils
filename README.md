# vBulletinThreadUtils
A collection of utils to extract information from vBulletinForums.

vBulletinSearch
Searchs the forum for threads.

vBulletinThreadParser
Parses a thread an extracts all the messages of a given user. Then it creates an outuput file that resembles the 
original thread but only with that user messages.

If we are using the vBulletinSearch thread list it will also generate an index page with all the threads that
appeared in the search

Generating the output files:
This script relies on some resource files to generate its output so they have the same look and feel as the parsed forum. 
This files should contain the <head> section used by the forum.

- resources\search_index_header.txt The header file from the search page in the parsed vBulletin forum.
- resources\page_header.txt The header file from the parsed vBulletin forum.
- resources\index_file_entry_pattern.txt It specifies the format of a search result in the forum.

vBulletingThreadDateParser
Parses a thread an extracts when a given username has posted its messages. It then creates a histogram with
the amount of messages each hour of each day of the week.

Config file sections:
- [VBULLETIN]: the user used to log into vBulletin. 
Specify 'logname', 'password' and 'base_url' (in the format https://www.some_forum.com/forum/).
- [SEARCHUSER]: in 'username' we specify the user we will use to filter the threads messages 
with vBulletinThreadParser
- [OPERATIONMODE]: specifies what kind of parsing we will use. Each of these operation modes will
have its own section with the required data.
- [SINGLETHREAD]: parses only a thread using 'thread_id' (thread URL will be 
base_url/showthread.php?t=thread_id) and creates a file with the messages of the user specified in
the SEARCHUSER section.
- [SEARCHTHREADS]: uses the vBulletin search engine to search thread with 'search_words' in its title.
You can also specify other parameters as 'replylimit' or 'forumchoice[]' to refine your results.


To do:
- Read from config file (done).
- Operation mode switch (done).
- Single thread processing instead of search result processing (done).
- Save external images.
- Refine search using config file parameters.
- Read HTML header instead of using local files.
