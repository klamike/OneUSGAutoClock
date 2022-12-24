## Configuration file for oneusg.py
import shutil

DEFAULT_HOURS_TO_CLOCK = 8

USERNAME = 'USERNAME_HERE'
PASSWORD = 'PASSWORD_HERE'

CHROMEDRIVER_PATH = shutil.which("chromedriver")

FAIL_PING_URL = 'FAILURE_PING_URL_HERE' # including the /fail at the end

RESEARCH_LOGIN_URL='https://selfservice.hprod.onehcm.usg.edu/psc/hprodsssso_newwin/HCMSS/HRMS/c/TL_EMPLOYEE_FL.TL_RPT_TIME_FLU.GBL?EMPDASHBD=Y&tW=1&tH=1&ICDoModeless=1&ICGrouplet=3&bReload=y&nWidth=236&nHeight=163&TL_JOB_CHAR=0'
TA_LOGIN_URL='https://selfservice.hprod.onehcm.usg.edu/psc/hprodsssso_newwin/HCMSS/HRMS/c/TL_EMPLOYEE_FL.TL_RPT_TIME_FLU.GBL?EMPDASHBD=Y&tW=1&tH=1&ICDoModeless=1&ICGrouplet=3&bReload=y&nWidth=236&nHeight=163&TL_JOB_CHAR=1'
# if you work multiple jobs through OneUSG, the number at the end of the URL below corresponds to the job's position in the dropdown.
# to double check, you can inspect element and see the "value" attribute of the corresponding dropdown option.
