# vBulletinThreadUtils
A collection of utils to extract information from .vBulletinForums.

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
Also some parameters to config how to store the threads:
  - output_dir where to store everythin
  - save_images download the images found in the thread to local storage
  - http_server_root specifies the root of a local HTTP server so proper image src attributes 
  can be generated in the HTML output.

- [FILTERUSER]: in 'username' we specify the user we will use to filter the threads messages 
with vBulletinThreadParser
- [OPERATIONMODE]: specifies what kind of parsing we will use. Each of these operation modes will
have its own section with the required data.
- [SINGLETHREAD]: parses only a thread using 'thread_id' (thread URL will be 
base_url/showthread.php?t=thread_id) and creates a file with the messages of the user specified in
the SEARCHUSER section.
- [SEARCHTHREADS]: uses the vBulletin search engine to search thread with 'search_words' in its title.
You can also specify other parameters:
  - search_user: Searches only for threads started by given user.
  - 'replylimit' to filter threads with more or less posts than a given number.
  - 'forumchoice[]' to refine your results by subforum.
  - Strict search: vBulletin search engine finds threads where any of the keywords provided are in the title. 
use this parameter to filter search results.


To do:
- Refine search using config file parameters.
- Read HTML header instead of using local files.
- Search user as post author and not only thread author.  
- Read from config file (done).
- Operation mode switch (done).
- Single thread processing instead of search result processing (done).
- Save external images (done).
- Search by user and filter by user using separate values (done).
- Strict search (done).  
- If filter user is empty we save the whole thread (done).
- Split parsing and writing to file (done).
