## Copyright (C) 2014 Bitergia
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
## This file is a part of GrimoireLib
##  (an Python library for the MetricsGrimoire and vizGrimoire systems)
##
##
## Authors:
##   Alvaro del Castillo <acs@bitergia.com>

""" Wikimedia specific Metrics for the source code review system """

from datetime import datetime, timedelta
import logging
import MySQLdb
from numpy import median, average

from GrimoireUtils import completePeriodIds, checkListArray, medianAndAvgByPeriod, removeDecimals
from metrics import Metrics
from metrics_filter import MetricFilters
from SCR import SCR

class TimeToReviewPendingSCR(Metrics):
    """
        Update time: last update in a review
        Upload time: last patch uploaded to the review (not all reviews have patches)
    """
    id = "review_time_pending_total"
    name = "Total Review Time Pending"
    desc = "Total time to review for pending reviews"
    data_source = SCR

    def get_agg(self):
        # Show review and update time for all pending reviews 
        # and just for reviews pending for reviewers
        reviewers_pending = True

        startdate = self.filters.startdate
        enddate = self.filters.enddate
        identities_db = self.db.identities_db
        type_analysis =  self.filters.type_analysis
        bots = []

        # Review time
        q = self.db.GetTimeToReviewPendingQuerySQL(startdate, enddate, identities_db,
                                                   type_analysis, bots)
        data = self.db.ExecuteQuery(q)
        data = data['revtime']
        if (isinstance(data, list) == False): data = [data]
        if (len(data) == 0):
            ttr_median = float("nan")
            ttr_avg = float("nan")
        else:
            ttr_median = median(removeDecimals(data))
            ttr_avg = average(removeDecimals(data))

        # Review time for reviewers
        q = self.db.GetTimeToReviewPendingQuerySQL(startdate, enddate,identities_db,
                                                   type_analysis, bots, False, reviewers_pending)
        data = self.db.ExecuteQuery(q)
        data = data['revtime']
        if (isinstance(data, list) == False): data = [data]
        if (len(data) == 0):
            ttr_reviewers_median = float("nan")
            ttr_reviewers_avg = float("nan")
        else:
            ttr_reviewers_median = median(removeDecimals(data))
            ttr_reviewers_avg = average(removeDecimals(data))

        # Update time
        q = self.db.GetTimeToReviewPendingQuerySQL (startdate, enddate,identities_db,
                                                    type_analysis, bots, True)
        data = self.db.ExecuteQuery(q)
        data = data['revtime']
        if (isinstance(data, list) == False): data = [data]
        if (len(data) == 0):
            ttr_median_update = float("nan")
            ttr_avg_update = float("nan")
        else:
            ttr_median_update = median(removeDecimals(data))
            ttr_avg_update = average(removeDecimals(data))

        # Update time for reviewers
        q = self.db.GetTimeToReviewPendingQuerySQL (startdate, enddate, identities_db,
                                                    type_analysis, bots, True, reviewers_pending)
        data = self.db.ExecuteQuery(q)
        data = data['revtime']
        if (isinstance(data, list) == False): data = [data]
        if (len(data) == 0):
            ttr_reviewers_median_update = float("nan")
            ttr_reviewers_avg_update = float("nan")
        else:
            ttr_reviewers_median_update = median(removeDecimals(data))
            ttr_reviewers_avg_update = average(removeDecimals(data))

        # Upload time
        q = self.db.GetTimeToReviewPendingQuerySQL (startdate, enddate,identities_db,
                                                    type_analysis, bots, False, False, True)
        data = self.db.ExecuteQuery(q)
        data = data['revtime']
        if (isinstance(data, list) == False): data = [data]
        if (len(data) == 0):
            ttr_median_update = float("nan")
            ttr_avg_update = float("nan")
        else:
            ttr_median_upload = median(removeDecimals(data))
            ttr_avg_upload = average(removeDecimals(data))

        # Upload time for reviewers
        q = self.db.GetTimeToReviewPendingQuerySQL (startdate, enddate, identities_db,
                                                    type_analysis, bots, False, reviewers_pending, True)
        data = self.db.ExecuteQuery(q)
        data = data['revtime']
        if (isinstance(data, list) == False): data = [data]
        if (len(data) == 0):
            ttr_reviewers_median_upload = float("nan")
            ttr_reviewers_avg_upload = float("nan")
        else:
            ttr_reviewers_median_upload = median(removeDecimals(data))
            ttr_reviewers_avg_upload = average(removeDecimals(data))


        time_to = {"review_time_pending_days_median":ttr_median,
                   "review_time_pending_days_avg":ttr_avg,
                   "review_time_pending_ReviewsWaitingForReviewer_days_median":ttr_reviewers_median,
                   "review_time_pending_ReviewsWaitingForReviewer_days_avg":ttr_reviewers_avg,
                   "review_time_pending_update_days_median":ttr_median_update,
                   "review_time_pending_update_days_avg":ttr_avg_update,
                   "review_time_pending_update_ReviewsWaitingForReviewer_days_median":ttr_reviewers_median_update,
                   "review_time_pending_update_ReviewsWaitingForReviewer_days_avg":ttr_reviewers_avg_update,
                   "review_time_pending_upload_days_median":ttr_median_upload,
                   "review_time_pending_upload_days_avg":ttr_avg_upload,
                   "review_time_pending_upload_ReviewsWaitingForReviewer_days_median":ttr_reviewers_median_upload,
                   "review_time_pending_upload_ReviewsWaitingForReviewer_days_avg":ttr_reviewers_avg_upload
                   }
        return time_to

    def get_ts(self):
        # Get all reviews pending time for each month and compute the median.
        # Return a list with all the medians for all months

        def get_date_from_month(monthid):
            # month format: year*12+month
            year = (monthid-1) / 12
            month = monthid - year*12
            # We need the last day of the month
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            current = str(year)+"-"+str(month)+"-"+str(last_day)
            return (current)

        # SQL for all, for updated  or for waiting for reviewer reviews
        def get_sql(month, updated=False, reviewers = False, uploaded = False):
            current = get_date_from_month(month)
            # List of pending reviews before a date: time from new time and from last update
            fields  = "TIMESTAMPDIFF(SECOND, submitted_on, '"+current+"')/(24*3600) AS newtime,"
            if (updated):
                fields = "TIMESTAMPDIFF(SECOND, mod_date, '"+current+"')/(24*3600) AS updatetime,"
            if (uploaded):
                fields = "TIMESTAMPDIFF(SECOND, comm.submitted_on, '"+current+"')/(24*3600) AS uploadtime,"
            fields += " YEAR(i.submitted_on)*12+MONTH(i.submitted_on) as month"
            tables = "issues i, people, issues_ext_gerrit ie "
            if (uploaded): tables += ", comments comm"
            if reviewers:
                q_last_change = self.db.get_sql_last_change_for_issues_new()
                tables += ", changes ch, (%s) t1" % q_last_change
            tables = tables + self.db.GetSQLReportFrom(identities_db, type_analysis)
            filters = " people.id = i.submitted_by "
            filters += self.db.GetSQLReportWhere(type_analysis, self.db.identities_db)
            filters += " AND status<>'MERGED' AND status<>'ABANDONED' "
            # https://bugzilla.wikimedia.org/show_bug.cgi?id=66283
            filters += " AND summary not like '%WIP%' "
            filters += " AND ie.issue_id  = i.id "
            if (uploaded): filters += " AND comm.issue_id  = i.id AND comm.text like '%Patch Set%Verified%' "
            if reviewers:
                filters += """
                    AND i.id = ch.issue_id  AND t1.id = ch.id
                    AND (ch.field='CRVW' or ch.field='Code-Review' or ch.field='Verified' or ch.field='VRIF')
                    AND (ch.new_value=1 or ch.new_value=2)
                """

            if (self.db.GetIssuesFiltered() != ""): filters += " AND " + self.db.GetIssuesFiltered()

            # All reviews before the month: accumulated key point
            filters += " HAVING month<= " + str(month)
            # Not include future submissions for current month analysis
            if (updated):
                filters += " AND updatetime >= 0"
            elif (uploaded):
                filters += " AND uploadtime >= 0"
            else:
                filters += " AND newtime >= 0"
            if (uploaded): " GROUP by comm.issued_id "
            filters += " ORDER BY  i.submitted_on"
            q = self.db.GetSQLGlobal('i.submitted_on', fields, tables, filters,
                        startdate,enddate)

            print(q)

            return q

        def get_values_median(values):
            if not isinstance(values, list): values = [values]
            values = removeDecimals(values)
            if (len(values) == 0): values = float('nan')
            else: values = median(values)
            return values

        startdate = self.filters.startdate
        enddate = self.filters.enddate
        identities_db = self.db.identities_db
        type_analysis =  self.filters.type_analysis
        period = self.filters.period
        bots = []

        start = datetime.strptime(startdate, "'%Y-%m-%d'")
        end = datetime.strptime(enddate, "'%Y-%m-%d'")

        if (period != "month"):
            logging.error("Period not supported in " + self.id  + " " + period)
            return None

        start_month = start.year*12 + start.month
        end_month = end.year*12 + end.month
        months = end_month - start_month
        acc_pending_time_median = {"month":[],
                                   "review_time_pending_days_acc_median":[],
                                   "review_time_pending_update_days_acc_median":[],
                                   "review_time_pending_upload_days_acc_median":[],
                                   "review_time_pending_ReviewsWaitingForReviewer_days_acc_median":[],
                                   "review_time_pending_update_ReviewsWaitingForReviewer_days_acc_median":[],
                                   "review_time_pending_upload_ReviewsWaitingForReviewer_days_acc_median":[]}

        for i in range(0, months+1):
            acc_pending_time_median['month'].append(start_month+i)

            reviews = self.db.ExecuteQuery(get_sql(start_month+i))
            values = get_values_median(reviews['newtime'])
            acc_pending_time_median['review_time_pending_days_acc_median'].append(values)

            reviews = self.db.ExecuteQuery(get_sql(start_month+i, True))
            values = get_values_median(reviews['updatetime'])
            acc_pending_time_median['review_time_pending_update_days_acc_median'].append(values)

            # upload time
            reviews = self.db.ExecuteQuery(get_sql(start_month+i, False, False, True))
            values = get_values_median(reviews['uploadtime'])
            acc_pending_time_median['review_time_pending_upload_days_acc_median'].append(values)

            # Now just for reviews waiting for Reviewer
            reviews = self.db.ExecuteQuery(get_sql(start_month+i, False, True))
            values = get_values_median(reviews['newtime'])
            acc_pending_time_median['review_time_pending_ReviewsWaitingForReviewer_days_acc_median'].append(values)

            reviews = self.db.ExecuteQuery(get_sql(start_month+i, True, True))
            values = get_values_median(reviews['updatetime'])
            acc_pending_time_median['review_time_pending_update_ReviewsWaitingForReviewer_days_acc_median'].append(values)

            reviews = self.db.ExecuteQuery(get_sql(start_month+i, False, True, True))
            values = get_values_median(reviews['uploadtime'])
            acc_pending_time_median['review_time_pending_upload_ReviewsWaitingForReviewer_days_acc_median'].append(values)

        # Normalize values removing NA and converting to 0. Maybe not a good idea.
        for m in acc_pending_time_median.keys():
            for i in range(0,len(acc_pending_time_median[m])):
                acc_pending_time_median[m][i] = float(acc_pending_time_median[m][i])

        return completePeriodIds(acc_pending_time_median, self.filters.period,
                                 self.filters.startdate, self.filters.enddate)
