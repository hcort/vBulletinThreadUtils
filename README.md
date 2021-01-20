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

To do:
- Read some parameters from config file.
- Operation mode switch.
- Single thread processing instead of search result processing.

