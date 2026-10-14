# Principles of Epidemiology | Lesson 2 - Section 3
URL: https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/lesson2/section3.html

Principles of Epidemiology | Lesson 2 - Section 3

## Section 3: Frequency Distributions

Look again at the data in Table 2.1. How many of the cases (or case-patients) are male?

When a database contains only a limited number of records, you can easily pick out the information you need directly from the raw data. By scanning the 5 th column, you can see that 12 of the 20 case-patients are male.

With larger databases, however, picking out the desired information at a glance becomes increasingly difficult. To facilitate the task, the variables can be summarized into tables called frequency distributions.

A frequency distribution displays the values a variable can take and the number of persons or records with each value. For example, suppose you have data from a study of women with ovarian cancer and wish to look at parity, that is, the number of times each woman has given birth. To construct a frequency distribution that displays these data:

- First, list all the values that the variable parity can take, from the lowest possible value to the highest.
- Then, for each value, record the number of women who had that number of births (twins and other multiple-birth pregnancies count only once).

To create a frequency distribution from a data set in Analysis Module:

Select frequencies, then choose variable.

Table 2.4 displays what the resulting frequency distribution would look like. Notice that the frequency distribution includes all values of parity between the lowest and highest observed, even though there were no women for some values. Notice also that each column is clearly labeled, and that the total is given in the bottom row.

Table 2.4 Distribution of Case-Subjects by Parity (Ratio-Scale Variable), Ovarian Cancer Study, CDC

| Parity | Number of Cases |
| --- | --- |
| 0 | 45 |
| 1 | 25 |
| 2 | 43 |
| 3 | 32 |
| 4 | 22 |
| 5 | 8 |
| 6 | 2 |
| 7 | 0 |
| 8 | 1 |
| 9 | 0 |
| 10 | 1 |
| Total | 179 |

Data Sources: Lee NC, Wingo PA, Gwinn ML, Rubin GL, Kendrick JS, Webster LA, Ory HW. The reduction in risk of ovarian cancer associated with oral contraceptive use. N Engl J Med 1987;316: 650–5. Centers for Disease Control Cancer and Steroid Hormone Study. Oral contraceptive use and the risk of ovarian cancer. JAMA 1983;249:1596–9.

Table 2.4 displays the frequency distribution for a continuous variable. Continuous variables are often further summarized with measures of central location and measures of spread. Distributions for ordinal and nominal variables are illustrated in Tables 2.5 and 2.6, respectively. Categorical variables are usually further summarized as ratios, proportions, and rates (discussed in Lesson 3).

Table 2.5 Distribution of Cases by Stage of Disease (Ordinal-Scale Variable), Ovarian Cancer Study, CDC

| | Cases | |
| --- | --- | --- |
| Stage | Number | Percent |
| I | 45 | 20 |
| II | 11 | 5 |
| III | 104 | 58 |
| IV | 30 | 17 |
| Total | 179 | 100 |

Data Sources: Lee NC, Wingo PA, Gwinn ML, Rubin GL, Kendrick JS, Webster LA, Ory HW. The reduction in risk of ovarian cancer associated with oral contraceptive use. N Engl J Med 1987;316: 650–5. Centers for Disease Control Cancer and Steroid Hormone Study. Oral contraceptive use and the risk of ovarian cancer. JAMA 1983;249:1596–9.

Table 2.6 Distribution of Cases by Enrollment Site (Nominal-Scale Variable), Ovarian Cancer Study, CDC

| | Cases | |
| --- | --- | --- |
| Enrollment Site | Number | Percent |
| Atlanta | 18 | 10 |
| Connecticut | 39 | 22 |
| Detroit | 35 | 20 |
| Iowa | 30 | 17 |
| New Mexico | 7 | 4 |
| San Francisco | 33 | 18 |
| Seattle | 9 | 5 |
| Utah | 8 | 4 |
| Total | 179 | 100 |

Data Sources: Lee NC, Wingo PA, Gwinn ML, Rubin GL, Kendrick JS, Webster LA, Ory HW. The reduction in risk of ovarian cancer associated with oral contraceptive use. N Engl J Med 1987;316: 650–5. Centers for Disease Control Cancer and Steroid Hormone Study. Oral contraceptive use and the risk of ovarian cancer. JAMA 1983;249:1596–9.

#### Epi Info Demonstration: Creating a Frequency Distribution

Scenario: In Oswego, New York, numerous people became sick with gastroenteritis after attending a church picnic. To identify all who became ill and to determine the source of illness, an epidemiologist administered a questionnaire to almost all of the attendees. The data from these questionnaires have been entered into an Epi Info file called Oswego.

In the outbreak that occurred in Oswego, how many of the participants became ill?

In Epi Info: Select Analyzing Data. 

Select Read (Import). The default data set should be Sample.mdb. Under Views, scroll down to view OSWEGO, and double click, or click once and then click OK.

Select Frequencies. Then click on the down arrow beneath Frequency of, scroll down and select ILL, then click OK.

 The resulting frequency distribution should indicate 46 ill persons, and 29 persons not ill.

Your Turn:

How many of the Oswego picnic attendees drank coffee? [Answer: 31]

### Exercise 2.2

At an influenza immunization clinic at a retirement community, residents were asked in how many previous years they had received influenza vaccine. The answers from the first 19 residents are listed below. Organize these data into a frequency distribution.

2, 0, 3, 1, 0, 1, 2, 2, 4, 8, 1, 3, 3, 12, 1, 6, 2, 5, 1

 Last Reviewed: May 18, 2012
