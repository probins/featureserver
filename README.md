Featureserver
=============
This is an updated version of FeatureServer (featureserver.org).

Master branch is the version in svn.osgeo.org/featureserver/trunk/featureserver - trunk version is a much improved version from the last release 1.12. vectorformats/ and web_request/ are pulled in by svn checkout.

I also use the 3rd-party geohash/ (used by the appengine backend) and simplejson/ (used by GeoJSON vectorformat), but these are not in this repo.


Changes
=======
The commit in mychanges branch is the changes I have made. These were all submitted on the mailing list, but there has been little support for the last couple of years, and they were never committed. 

FeatureServer/DataSource/DBM: allow non-ASCII chars in queries (UTF-8)
FeatureServer/DataSource/SQLite: 
- add not-equal query-action-type
- remove unnecessary commits
- fix update of attributes
- update date_modified if geometry changed
vectorformats/Formats/GeoJSON: stop floats from creating unnecessary decimals, e.g. 43.12 output as 43.12 not 43.119999999999997
vectorformats/Formats/KML:
- replace deprecated MetaData for attributes with ExtendedData
- stop reversing sequence of linestring nodes
- convert linestrings to floats
- remove description (output as any other ExtendedData attribute)
- handle whitespace on read
vectorformats/Formats/WKT: correct typo and make geometry types consistently upper-case
web_request/handlers: allow for url-encoding in querystring
