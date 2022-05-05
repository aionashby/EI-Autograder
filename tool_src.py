
# this tool is for daily EI aggregation
# input: a csv file of Canvas gradebook that only contains student information and daily EI computation needed
#        new column name
# output: a csv file with basic columns plus new column name
import sys
import pandas as pd
from datetime import datetime, timedelta
import pytz

pd.set_option('display.max_columns', 200)
pd.set_option('display.max_rows', 200)


# check whether actual time is in [expected_start, expected_end]
# if in then return 1, otherwise return 0


def is_in_time(expected_start, expected_end, actual):
    if (actual >= expected_start and actual < expected_end):
        return 1
    else:
        return 0


def main():
    print("Daily EI tool starts running.")
    if len(sys.argv) < 8:
        print("Missing argument.")
        print("7 arguments needed. In the following order: ")
        print("quiz csv file path")
        print("gradebook csv file path")
        print("column name of generated weekly score")
        print("start time of the week in YYYY-MM-DD HH:MM:SS (US/Eastern)")
        print("how many days after the starting time will be graded")
        print("how many days counted as full grade for the week (You can grade for 7 days but consider 5 submissions are enough for full grade)")
        print("full grade for one week's daily EI (currently 5)")
        return
    quiz_csv_name = sys.argv[1]
    grade_book_name = sys.argv[2]
    new_col_name = sys.argv[3]
    # start time of day 1
    start_time_str = sys.argv[4]
    # grading_days
    grading_days = int(sys.argv[5])
    # how many days it need to get full mark
    full_mark_days = int(sys.argv[6])
    # full grade (currently 5)
    full_grade = int(sys.argv[7])
    # input start time is in US/Eastern
    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    eastern_timezone = pytz.timezone('US/Eastern')
    start_time = eastern_timezone.localize(start_time)
    print("Input quiz csv file is: ", quiz_csv_name)
    print("Proposed new column name is: ", new_col_name)
    print("Output csv file is automatically named with test_output.csv")
    print("Output csv file with names of distressed students automatically named with distressed_names.csv")
    print("Output csv file with names of repeating students automatically named with repeating_names.csv")
    # read csv and store into dataframe raw_quiz_grade
    raw_quiz_grade = pd.read_csv(quiz_csv_name)
    # sort raw_quiz_grade first by name and then by submitted
    quiz_grade = raw_quiz_grade.sort_values(
        ['name', 'submitted'], ascending=True)
    # convert time stamp to Eastern time
    quiz_grade["et_submitted"] = pd.to_datetime(
        quiz_grade['submitted'], format="%Y-%m-%d %H:%M:%S %Z").dt.tz_convert('US/Eastern')

    #quiz_grade_gb = raw_quiz_grade.groupby("name").agg()
    unique_id_list = pd.unique(quiz_grade["id"])
    daily_EI_grades = pd.DataFrame(unique_id_list, columns=['id'])

    #push to github and add readme explaining code

    #list of words to scan and look out for
    key_words = ['depressed', 'stressed', 'frustrated', 'hopeless']
    distressed_names = []
    repeating_names = []

    #dictionary containing names of students in distress mapping to how many times they used distressed words
    distressed_dict = dict()

    #searching each response for distress words and repeating submissions and adding names to respective list
    for row in raw_quiz_grade.itertuples():
        if any(word in str(row) for word in key_words) and (row.name + ' ' + str(row.sis_id)) not in distressed_dict:
            distressed_dict[(row.name + ' ' + str(row.sis_id))] = 1
        elif any(word in str(row) for word in key_words) and (row.name + ' ' + str(row.sis_id)) in distressed_dict:
            distressed_dict[(row.name + ' ' + str(row.sis_id))] += 1
        if row._9 == row._11 == row._13 == row._15 == row._17:
            repeating_names.append(row.name + ' ' + str(row.sis_id))
    
    #adding distressed names to dictionary
    for key in distressed_dict:
        distressed_names.append(key + ' ' + str(distressed_dict[key]))
         
    pd.DataFrame(distressed_names).to_csv("distressed_names.csv", index=False)
    pd.DataFrame(repeating_names).to_csv("repeating_names.csv", index=False)

    daily_EI_grades.set_index('id', inplace=True)

    # build an array for grading days from start_time
    days_start_time = [start_time +
                       timedelta(days=i) for i in range(grading_days)]

    # nested for loop, outer loop for each day in the week starting with given start time
    # inner loop for each student's submission
    for day_start in days_start_time:
        expect_start = day_start
        expect_end = day_start + timedelta(days=1)
        today_colname = expect_start.strftime("%Y-%m-%d %H:%M:%S %Z")
        daily_EI_grades[today_colname] = 0

        for index, row in quiz_grade.iterrows():
            submit_time = row['et_submitted']
            if (is_in_time(expect_start, expect_end, submit_time)):
                daily_EI_grades.loc[row['id'], today_colname] = 1

    # 'weekly daily EI count' is the column for total submitted days for one student
    daily_EI_grades['weekly daily EI count'] = daily_EI_grades.sum(axis=1)
    # 'full mark days' is the auxillary column for full mark days
    daily_EI_grades['full mark days'] = full_mark_days
    s1 = pd.Series(daily_EI_grades['weekly daily EI count'])
    s2 = pd.Series(daily_EI_grades['full mark days'])
    daily_EI_grades['weekly daily EI grade'] = pd.concat(
        [s1, s2], axis=1).min(axis=1) / full_mark_days * full_grade

    # update grade book csv
    grade_book = pd.read_csv(grade_book_name, skiprows=[
                             1, 2])
    grade_book = grade_book[['Student', 'ID']]
    grade_book[new_col_name] = grade_book["ID"].map(
        daily_EI_grades['weekly daily EI grade'])

    # output
    grade_book.to_csv("test_output.csv", index=False)


if __name__ == "__main__":
    main()
