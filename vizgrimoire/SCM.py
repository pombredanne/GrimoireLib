## Copyright (C) 2012, 2013 Bitergia
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details. 
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
##
##
## Queries for SCM data analysis
##
## Authors:
##   Jesus M. Gonzalez-Barahona <jgb@bitergia.com>
##   Daniel Izquierdo <dizquierdo@bitergia.com>
##   Alvaro del Castillo <acs@bitergia.com>


import os, logging

from GrimoireSQL import GetSQLGlobal, GetSQLPeriod
# TODO integrate: from GrimoireSQL import  GetSQLReportFrom 
from GrimoireSQL import ExecuteQuery, BuildQuery
from GrimoireUtils import GetPercentageDiff, GetDates, completePeriodIds
from GrimoireUtils import createJSON, getPeriod, get_subprojects
from data_source import DataSource
from filter import Filter
from metrics_filter import MetricFilters
from query_builder import DSQuery

class SCM(DataSource):
    _metrics_set = []

    @staticmethod
    def get_db_name():
        return "db_cvsanaly"

    @staticmethod
    def get_name():
        return "scm"

    @staticmethod
    def get_date_init(startdate, enddate, identities_db = None, type_analysis = None):
        fields = "DATE_FORMAT (min(s.date), '%Y-%m-%d') as first_date"
        tables = "scmlog s"
        filters = ""
        q = GetSQLGlobal('s.date',fields, tables, filters, startdate, enddate)
        return ExecuteQuery(q)

    @staticmethod
    def get_date_end(startdate, enddate, identities_db = None, type_analysis = None):
        fields = "DATE_FORMAT (max(s.date), '%Y-%m-%d') as last_date"
        tables = "scmlog s"
        filters = ""
        q = GetSQLGlobal('s.date',fields, tables, filters, startdate, enddate)
        return ExecuteQuery(q)

    @staticmethod
    def get_url():
        q = "select uri as url,type from repositories limit 1"
        return (ExecuteQuery(q))

    @staticmethod
    def get_evolutionary_data (period, startdate, enddate, identities_db, filter_ = None):
        metrics = DataSource.get_metrics_data(SCM, period, startdate, enddate, identities_db, filter_, True)
        if filter_ is not None: studies = {}
        else:
            studies = DataSource.get_studies_data(SCM, period, startdate, enddate, True)
        evol_data = dict(metrics.items()+studies.items())

        return evol_data

    @staticmethod
    def create_evolutionary_report (period, startdate, enddate, destdir, i_db, filter_ = None):
        data =  SCM.get_evolutionary_data (period, startdate, enddate, i_db, filter_)
        filename = SCM().get_evolutionary_filename()
        createJSON (data, os.path.join(destdir, filename))

    @staticmethod
    def get_agg_data (period, startdate, enddate, identities_db, filter_= None):
        metrics = DataSource.get_metrics_data(SCM, period, startdate, enddate, 
                                              identities_db, filter_, False)
        if filter_ is not None: studies = {}
        else:
            studies = DataSource.get_studies_data(SCM, period, startdate, enddate, False)
        agg = dict(metrics.items()+studies.items())

        if (filter_ is None):
            static_url = SCM.get_url()
            agg = dict(agg.items() + static_url.items())

        return agg

    @staticmethod
    def create_agg_report (period, startdate, enddate, destdir, i_db, filter_= None):
        data = SCM.get_agg_data (period, startdate, enddate, i_db, filter_)
        filename = SCM().get_agg_filename()
        createJSON (data, os.path.join(destdir, filename))

    @staticmethod
    def get_project_top_companies (project, startdate, enddate, limit):
        # Hack to get a SCMQuery
        dbcon = SCM.get_metrics_set(SCM)[0].db
        top_companies = dbcon.get_project_top_companies (project, startdate, enddate, limit)
        return top_companies

    @staticmethod
    def get_project_top_authors (project, startdate, enddate, npeople):
        # Hack to get a SCMQuery
        dbcon = SCM.get_metrics_set(SCM)[0].db
        top_authors = dbcon.get_project_top_authors (project, startdate, enddate, npeople)
        return top_authors

    @staticmethod
    def get_repository_top_authors (repo, startdate, enddate, npeople):
        # Hack to get a SCMQuery
        dbcon = SCM.get_metrics_set(SCM)[0].db
        top_authors = dbcon.get_repository_top_authors (repo, startdate, enddate, npeople)
        return top_authors


    @staticmethod
    def get_top_data_companies (startdate, enddate, i_db, filter_, npeople):
        top = {}
        mcompanies = DataSource.get_metrics("companies", SCM)
        if mcompanies is None: return top
        period = None
        if filter_ is not None:
            if filter_.get_name() == "project":
                # TODO missing companies_out
                companies_out = mcompanies.filters.companies_out
                people_out = None
                mfilter = MetricFilters(period, startdate, enddate, filter_.get_type_analysis(), npeople, people_out, companies_out)
                top = mcompanies.get_list(mfilter)
        return top


    @staticmethod
    def get_top_data_authors (startdate, enddate, i_db, filter_, npeople):
        top = {}
        mauthors = DataSource.get_metrics("authors", SCM)
        if mauthors is None: return top
        period = None
        type_analysis = None
        if filter_ is not None:
            type_analysis = filter_.get_type_analysis()
        mfilter = MetricFilters(period, startdate, enddate, type_analysis, npeople)

        if filter_ is None:
            top['authors.'] = mauthors.get_list(mfilter, 0)
            top['authors.last month'] = mauthors.get_list(mfilter, 31)
            top['authors.last year'] = mauthors.get_list(mfilter, 365)
        elif filter_.get_name() in ["company","repository","project"]:
            if filter_.get_name() == "repository":
                top['authors.'] = mauthors.get_list(mfilter, 0)
                top['authors.last month'] = mauthors.get_list(mfilter, 31)
                top['authors.last year'] = mauthors.get_list(mfilter, 365)
            else:
                top = mauthors.get_list(mfilter) 
        else:
            logging.info("Top authors not support for " + filter_.get_name())
        return top

    @staticmethod
    def get_top_data (startdate, enddate, i_db, filter_, npeople):
        from report import Report
        top = {}
        data = SCM.get_top_data_authors (startdate, enddate, i_db, filter_, npeople)
        top = dict(top.items() + data.items())
        companies_on = False
        for filter_aux in Report.get_filters():
            if filter_aux.get_name() == "company": companies_on = True
        if companies_on:
            data = SCM.get_top_data_companies (startdate, enddate, i_db, filter_, npeople)
            top = dict(top.items() + data.items())
        return top

    @staticmethod
    def create_top_report (startdate, enddate, destdir, npeople, i_db):
        data = SCM.get_top_data (startdate, enddate, i_db, None, npeople)
        createJSON (data, destdir+"/"+SCM().get_top_filename())

    @staticmethod
    def get_filter_items(filter_, startdate, enddate, identities_db):
        items = None
        filter_name = filter_.get_name()

        if (filter_name == "repository"):
            metric = DataSource.get_metrics("repositories", SCM)
        elif (filter_name == "company"):
            metric = DataSource.get_metrics("companies", SCM)
        elif (filter_name == "country"):
            metric = DataSource.get_metrics("countries", SCM)
        elif (filter_name == "domain"):
            metric = DataSource.get_metrics("domains", SCM)
        elif (filter_name == "project"):
            metric = DataSource.get_metrics("projects", SCM)
        elif (filter_name == "people2"):
            metric = DataSource.get_metrics("people2", SCM)
        else:
            logging.error("SCM " + filter_name + " not supported")
            return items

        if metric is not None: items = metric.get_list()

        return items

    @staticmethod
    def get_filter_summary(filter_, period, startdate, enddate, identities_db, limit):
        summary = None
        filter_name = filter_.get_name()

        if (filter_name == "company"):
            summary =  GetCommitsSummaryCompanies(period, startdate, enddate, identities_db, limit)
        return summary

    @staticmethod
    def create_filter_report(filter_, period, startdate, enddate, destdir, npeople, identities_db):
        from report import Report
        items = Report.get_items()
        if items is None:
            items = SCM.get_filter_items(filter_, startdate, enddate, identities_db)
            if (items == None): return
            items = items['name']

        filter_name = filter_.get_name()

        if not isinstance(items, (list)):
            items = [items]

        fn = os.path.join(destdir, filter_.get_filename(SCM()))
        createJSON(items, fn)

        if filter_name in ("domain", "company", "repository"):
            items_list = {'name' : [], 'commits_365' : [], 'authors_365' : []}
        else:
            items_list = items

        for item in items :
            item_name = "'"+ item+ "'"
            logging.info (item_name)
            filter_item = Filter(filter_name, item)

            evol_data = SCM.get_evolutionary_data(period, startdate, enddate, identities_db, filter_item)
            fn = os.path.join(destdir, filter_item.get_evolutionary_filename(SCM()))
            createJSON(evol_data, fn)

            agg = SCM.get_agg_data(period, startdate, enddate, identities_db, filter_item)
            fn = os.path.join(destdir, filter_item.get_static_filename(SCM()))
            createJSON(agg, fn)

            if filter_name in ("domain", "company", "repository"):
                items_list['name'].append(item.replace('/', '_'))
                items_list['commits_365'].append(agg['commits_365'])
                items_list['authors_365'].append(agg['authors_365'])

            if filter_name in ("company","project","repository"):
                top_authors = SCM.get_top_data(startdate, enddate, identities_db, filter_item, npeople)
                fn = os.path.join(destdir, filter_item.get_top_filename(SCM()))
                createJSON(top_authors, fn)

        fn = os.path.join(destdir, filter_.get_filename(SCM()))
        createJSON(items_list, fn)

        if (filter_name == "company"):
            summary =  SCM.get_filter_summary(filter_, period, startdate, enddate, identities_db, 10)
            createJSON (summary, destdir+"/"+ filter_.get_summary_filename(SCM))

    @staticmethod
    def _check_report_all_data(data, filter_, startdate, enddate, idb,
                               evol = False, period = None):
        # Check per item data with group by people data
        items = SCM.get_filter_items(filter_, startdate, enddate, idb)
        id_field = DSQuery.get_group_field(filter_.get_name())
        id_field = id_field.split('.')[1] # remove table name
        for i in range(0,len(items['name'])):
            name = items['name'][i]
            logging.info("Checking " + name + " " + str(i) + "/" + str(len(items['name'])))
            if filter_.get_name() == "people2":
                upeople_id = items['id'][i]
                item = upeople_id
            else:
                item = name
            pos = data[id_field].index(name)

            type_analysis = [filter_.get_name(), item]
            filter_item = Filter(filter_.get_name(), item)

            if not evol:
                if filter_.get_name() == "people2":
                    agg = SCM.get_person_agg(upeople_id, startdate, enddate,
                                             idb, type_analysis)
                else:
                    agg = SCM.get_agg_data(period, startdate, enddate,
                                           idb, filter_item)
                assert agg['commits' ] == data['commits'][pos]
            else:
                if filter_.get_name() == "people2":
                    ts = SCM.get_person_evol(upeople_id, period,
                                             startdate, enddate, idb, type_analysis)
                else:
                    ts = SCM.get_evolutionary_data(period, startdate, enddate,
                                                   idb , filter_item)
                assert ts['commits'] == data['commits'][pos]

    @staticmethod
    def create_filter_report_all(filter_, period, startdate, enddate, destdir, npeople, identities_db):
        # New API for getting all metrics with one query
        check = False # activate to debug issues
        filter_name = filter_.get_name()
        if filter_name == "people2" or filter_name == "company":
            filter_all = Filter(filter_name, None)
            agg_all = SCM.get_agg_data(period, startdate, enddate,
                                       identities_db, filter_all)
            fn = os.path.join(destdir, filter_.get_static_filename_all(SCM()))
            createJSON(agg_all, fn)

            evol_all = SCM.get_evolutionary_data(period, startdate, enddate,
                                                 identities_db, filter_all)
            fn = os.path.join(destdir, filter_.get_evolutionary_filename_all(SCM()))
            createJSON(evol_all, fn)

            if check:
                SCM._check_report_all_data(evol_all, filter_, startdate, enddate,
                                           identities_db, True, period)
                SCM._check_report_all_data(agg_all, filter_, startdate, enddate,
                                           identities_db, False, period)
        else:
            raise Exception(filter_name +" does not support yet group by items sql queries")

    @staticmethod
    def get_top_people(startdate, enddate, identities_db, npeople):
        top_authors_data = SCM.get_top_data (startdate, enddate, identities_db, None, npeople)
        if "authors." not in top_authors_data.keys(): return None
        top = top_authors_data['authors.']["id"]
        top += top_authors_data['authors.last year']["id"]
        top += top_authors_data['authors.last month']["id"]
        # remove duplicates
        people = list(set(top))

        return people

    @staticmethod
    def get_person_evol(upeople_id, period, startdate, enddate, identities_db, type_analysis):
        evol_data = GetEvolPeopleSCM(upeople_id, period, startdate, enddate)
        evol_data = completePeriodIds(evol_data, period, startdate, enddate)
        return evol_data

    @staticmethod
    def get_person_agg(upeople_id, startdate, enddate, identities_db, type_analysis):
        agg = GetStaticPeopleSCM(upeople_id,  startdate, enddate)
        return agg

    # Studies implemented in R
    @staticmethod
    def create_r_reports(vizr, enddate, destdir):
        unique_ids = True
        # Demographics - created now with age study in Python
        # Demographics
        # vizr.ReportDemographicsAgingSCM(enddate, destdir, unique_ids)
        # vizr.ReportDemographicsBirthSCM(enddate, destdir, unique_ids)

    @staticmethod
    def _remove_people(people_id):
        # Remove from people
        q = "DELETE FROM people_upeople WHERE people_id='%s'" % (people_id)
        ExecuteQuery(q)
        q = "DELETE FROM people WHERE id='%s'" % (people_id)
        ExecuteQuery(q)

    @staticmethod
    def _remove_scmlog(scmlog_id):
        # Get actions and remove mappings
        q = "SELECT * from actions where commit_id='%s'" % (scmlog_id)
        res = ExecuteQuery(q)
        if 'id' in res:
            if not isinstance(res['id'], list): res['id'] = [res['id']]
            for action_id in res['id']:
                # action_files is a view
                # q = "DELETE FROM action_files WHERE action_id='%s'" % (action_id)
                # ExecuteQuery(q)
                q = "DELETE FROM file_copies WHERE action_id='%s'" % (action_id)
                ExecuteQuery(q)
        # actions_file_names is a VIEW
        # q = "DELETE FROM actions_file_names WHERE commit_id='%s'" % (scmlog_id)
        # ExecuteQuery(q)
        q = "DELETE FROM commits_lines WHERE commit_id='%s'" % (scmlog_id)
        ExecuteQuery(q)
        q = "DELETE FROM file_links WHERE commit_id='%s'" % (scmlog_id)
        ExecuteQuery(q)
        q = "SELECT tag_id from tag_revisions WHERE commit_id='%s'" % (scmlog_id)
        res = ExecuteQuery(q)
        for tag_id in res['tag_id']:
            q = "DELETE FROM tags WHERE id='%s'" % (tag_id)
            ExecuteQuery(q)
            q = "DELETE FROM tag_revisions WHERE tag_id='%s'" % (tag_id)
            ExecuteQuery(q)
        q = "DELETE FROM scmlog WHERE id='%s'" % (scmlog_id)
        ExecuteQuery(q)

    @staticmethod
    def remove_filter_data(filter_):
        uri = filter_.get_item()
        logging.info("Removing SCM filter %s %s" % (filter_.get_name(),filter_.get_item()))
        q = "SELECT * from repositories WHERE uri='%s'" % (uri)
        repo = ExecuteQuery(q)
        if 'id' not in repo:
            logging.error("%s not found" % (uri))
            return
        # Remove people
        def get_people_one_repo(field):
            return  """
                SELECT %s FROM (SELECT COUNT(DISTINCT(repository_id)) AS total, %s
                FROM scmlog
                GROUP BY %s
                HAVING total=1) t
                """ % (field, field, field)
        ## Remove committer_id that exists only in this repository
        q = """
            SELECT DISTINCT(committer_id) from scmlog
            WHERE repository_id='%s' AND committer_id in (%s)
        """  % (repo['id'],get_people_one_repo("committer_id"))
        res = ExecuteQuery(q)
        for people_id in res['committer_id']:
            SCM._remove_people(people_id)
        ## Remove author_id that exists only in this repository
        q = """
            SELECT DISTINCT(author_id) from scmlog
            WHERE repository_id='%s' AND author_id in (%s)
        """  % (repo['id'],get_people_one_repo("author_id"))
        res = ExecuteQuery(q)
        for people_id in res['author_id']:
            SCM._remove_people(people_id)
        # Remove people activity
        q = "SELECT id from scmlog WHERE repository_id='%s'" % (repo['id'])
        res = ExecuteQuery(q)
        for scmlog_id in res['id']:
            SCM._remove_scmlog(scmlog_id)
        # Remove files
        q = "SELECT id FROM files WHERE repository_id='%s'" % (repo['id'])
        res = ExecuteQuery(q)
        for file_id in res['id']:
            q = "DELETE FROM file_types WHERE file_id='%s'" % (file_id)
            ExecuteQuery(q)
            q = "DELETE FROM files WHERE id='%s'" % (file_id)
            ExecuteQuery(q)
        # Remove filter
        q = "DELETE from repositories WHERE id='%s'" % (repo['id'])
        ExecuteQuery(q)

    @staticmethod
    def get_query_builder():
        from query_builder import SCMQuery
        return SCMQuery

    @staticmethod
    def get_metrics_core_agg():
        m  = ['commits','authors','committers','branches','files','actions']
        m += ['added_lines','removed_lines', 'repositories']
        m += ['avg_commits', 'avg_files', 'avg_commits_author', 'avg_files_author']
        return m

    @staticmethod
    def get_metrics_core_ts():
        m  = ['commits','authors','committers','branches','files']
        m += ['added_lines','removed_lines','repositories']
        return m

    @staticmethod
    def get_metrics_core_trends():
        return ['commits','authors','files','lines']

#
# People
#

def GetTablesOwnUniqueIdsSCM () :
    return (' actions a, scmlog s, people_upeople pup')


def GetFiltersOwnUniqueIdsSCM () :
    return ('pup.people_id = s.author_id and s.id = a.commit_id ') 

def GetPeopleListSCM (startdate, enddate) :
    fields = "DISTINCT(pup.upeople_id) as pid, COUNT(distinct(s.id)) as total"
    tables = GetTablesOwnUniqueIdsSCM()
    filters = GetFiltersOwnUniqueIdsSCM()
    filters +=" GROUP BY pid ORDER BY total desc, pid"
    q = GetSQLGlobal('s.date',fields,tables, filters, startdate, enddate)

    data = ExecuteQuery(q)
    return (data)

def GetPeopleQuerySCM (developer_id, period, startdate, enddate, evol) :
    fields ='COUNT(distinct(s.id)) AS commits'
    tables = GetTablesOwnUniqueIdsSCM()
    filters = GetFiltersOwnUniqueIdsSCM()
    filters +=" AND pup.upeople_id="+str(developer_id)
    if (evol) :
        q = GetSQLPeriod(period,'s.date', fields, tables, filters,
                startdate, enddate)
    else :
        fields += ",DATE_FORMAT (min(s.date),'%Y-%m-%d') as first_date, "+\
                  "DATE_FORMAT (max(s.date),'%Y-%m-%d') as last_date"
        q = GetSQLGlobal('s.date', fields, tables, filters, 
                startdate, enddate)

    return (q)


def GetEvolPeopleSCM (developer_id, period, startdate, enddate) :
    q = GetPeopleQuerySCM (developer_id, period, startdate, enddate, True)

    data = ExecuteQuery(q)
    return (data)


def GetStaticPeopleSCM (developer_id, startdate, enddate) :
    q = GetPeopleQuerySCM (developer_id, None, startdate, enddate, False)

    data = ExecuteQuery(q)
    return (data)

def GetActiveAuthorsSCM(days, enddate):
    #return unique ids of active authors during "days" day
    # FIXME parameters should be: startdate and enddate
    q0 = "SELECT distinct(pup.upeople_id) as active_authors "+\
        "FROM actions a, scmlog s, people_upeople pup " +\
        "WHERE pup.people_id = s.author_id and a.commit_id = s.id and " +\
        "s.date >= (%s - INTERVAL %s day)"
    q1 = q0 % (enddate, days)
    data = ExecuteQuery(q1)
    return(data)

def GetActiveCommittersSCM(days, enddate):
    #return unique ids of active committers during "days" day
    # FIXME parameters should be: startdate and enddate
    q0 = "SELECT distinct(pup.upeople_id) as active_committers "+\
         "FROM actions a, scmlog s, people_upeople pup " +\
         "WHERE pup.people_id = s.committer_id and s.id = a.commit_id and " + \
         "s.date >= (%s - INTERVAL %s day)"
    q1 = q0 % (enddate, days)
    data = ExecuteQuery(q1)
    return(data)

def GetActivePeopleSCM(days, enddate):
    #Gets IDs of active people on the repository during last x days
    authors = GetActiveAuthorsSCM(days, enddate)
    committers = GetActiveCommittersSCM(days, enddate)
    people_scm = authors['active_authors'] + committers['active_committers']
    people_scm = list(set(people_scm))
    return(people_scm)

def GetCommunityMembers():
    #Gets IDs of all community members with no filter
    q = "SELECT DISTINCT(id) as members FROM upeople"
    data = ExecuteQuery(q)
    return(data['members'])

def top_files_modified () :
    # Top 10 modified files

    #FIXME: to be updated to use stardate and enddate values
    q = "select file_name, count(commit_id) as modifications "+\
        "from action_files a join files f on a.file_id = f.id  "+\
        "where action_type='M'  "+\
        "group by f.id  "+\
        "order by modifications desc limit 10; "	
    data = ExecuteQuery(q)
    return (data)	

def top_authors_year (year, limit) :
    # Given a year, this functions provides the top 10 authors 
    # of such year
    q = "SELECT u.id as id, u.identifier as authors, "+\
        "       count(distinct(s.id)) as commits "+\
        "FROM scmlog s, actions a, "+\
        "     people_upeople pup, "+\
        "     upeople u "+\
        "where s.id = a.commit_id and " +\
        "      s.author_id = pup.people_id and "+\
        "      pup.upeople_id = u.id and "+\
        "      year(s.date) = "+year+" "+\
        "group by u.identifier "+\
        "order by commits desc "+\
        "LIMIT " + limit

    data = ExecuteQuery(q)
    return (data)


def people () :
    # List of people participating in the source code development
 
    q = "select id,identifier from upeople"

    data = ExecuteQuery(q)
    return (data);

# Companies / Countries support

def scm_companies_countries_evol (identities_db, company, country, period, startdate, enddate) :

    rol = "author" #committer

    q = "SELECT ((to_days(s.date) - to_days("+startdate+")) div "+str(period)+") as id, "+\
        "count(s.id) AS commits, "+\
        "COUNT(DISTINCT(s."+rol+"_id)) as "+rol+"s "+\
        "FROM scmlog s,  "+\
        "     people_upeople pup, "+\
        "     "+identities_db+".countries ct, "+\
        "     "+identities_db+".upeople_countries upct, "+\
        "     "+identities_db+".companies com, "+\
        "     "+identities_db+".upeople_companies upcom "+\
        "WHERE pup.people_id = s."+rol+"_id AND "+\
        "      pup.upeople_id  = upct.upeople_id and "+\
        "      pup.upeople_id = upcom.upeople_id AND "+\
        "      upcom.company_id = com.id AND "+\
        "      upct.country_id = ct.id and "+\
        "      s.date >="+ startdate+ " and "+\
        "      s.date < "+ enddate+ " and "+\
        "      ct.name = '"+ country+ "' AND "+\
        "      com.name ='"+company+"' "+\
        "GROUP BY ((to_days(s.date) - to_days("+startdate+")) div "+str(period)+")"

    data = ExecuteQuery(q)	
    return (data)

##############
# Micro Studies
##############

def GetCommitsSummaryCompanies (period, startdate, enddate, identities_db, num_companies):
    # This function returns the following dataframe structrure
    # unixtime, date, week/month/..., company1, company2, ... company[num_companies -1], others
    # The 3 first fields are used for data and ordering purposes
    # The "companyX" fields are those that provide info about that company
    # The "Others" field is the aggregated value of the rest of the companies
    # Companies above num_companies will be aggregated in Others

    metric = DataSource.get_metrics("companies", SCM)
    companies = metric.get_list()
    companies = companies['name']

    first_companies = {}
    count = 1
    for company in companies:
        company_name = "'"+company+"'"
        type_analysis = ['company', company_name]
        mcommits = DataSource.get_metrics("commits", SCM)
        mfilter = MetricFilters(period, startdate, enddate, type_analysis)
        mfilter_orig = mcommits.filters
        mcommits.filters = mfilter
        commits = mcommits.get_ts()
        mcommits.filters = mfilter_orig
        # commits = EvolCommits(period, startdate, enddate, identities_db, ["company", company_name])
        # commits = completePeriodIds(commits, period, startdate, enddate)
        # Rename field commits to company name
        commits[company] = commits["commits"]
        del commits['commits']

        if (count <= num_companies):
            #Case of companies with entity in the dataset
            first_companies = dict(first_companies.items() + commits.items())
        else :
            #Case of companies that are aggregated in the field Others
            if 'Others' not in first_companies:
                first_companies['Others'] = commits[company]
            else:
                first_companies['Others'] = [a+b for a, b in zip(first_companies['Others'],commits[company])]
        count = count + 1

    #TODO: remove global variables...
    first_companies = completePeriodIds(first_companies, period, startdate, enddate)
    return(first_companies)
