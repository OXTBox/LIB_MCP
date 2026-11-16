lms
lms sever-start
lms load spark-x2.6-4b

REM Test it If you get JSON back listing models, that's your endpoint
curl http://localhost:1234/v1/models