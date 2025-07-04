# CoDeF
CoDeF: Comprehensive Design Framework for Advanced Mobility

# Web Application Deployment Guide

The CoDeF Web Application is written in Python and served using Uvicorn. It uses PostgreSQL as the database backend. This document explains how to deploy the service using Docker.
##1.	Prerequisites
Install Docker Desktop: https://docs.docker.com/desktop/
##2.	Source Code Setup
2.1 Extract the source code archive.
2.2	Open and edit the configuration file: CoDeF/web/.env.prod
  	![image](https://github.com/user-attachments/assets/2ae706c9-b3e1-4817-b9aa-98363db4834d)
 
###  DOMAIN: <domain>:<port number>
•	domain: The IP address or domain name to be used for the service.
Use localhost for local testing only. To allow access from other devices, specify a public IP or accessible domain name.
•	port number: The port to serve the application. Default is 8000.
If you wish to use a different port, also edit CoDeF/docker-compose.yaml:
Change the line 8000:8000 under app.ports to <your_port>:8000.
###  SECRET_KEY: A secret key used for JWT authentication. Any random string is acceptable.
###  DATABASE_URL: Database connection string. This must match the DB configuration in docker-compose.yaml. It is recommended to leave this as-is.
###  DATA_PATH: Path for storing user-uploaded and system-generated data.
Set this to data to use CoDeF/data.If your service does not provide username use sender address for connection.

• Email Configuration Fields:
•	MAIL_USERNAME: Email account username. If your mail provider does not separate username and sender address, use the full email address here.
•	MAIL_PASSWORD: Password or app-specific password for the email account.
•	MAIL_FROM: Sender email address.
•	MAIL_PORT: SMTP server port.
•	MAIL_SERVER: SMTP server address.
•	MAIL_FROM_NAME: Sender display name.
•	MAIL_STARTTLS: Enable for STARTTLS connections.
•	MAIL_SSL_TLS: Enable for TLS/SSL connections.
⚠️ Email settings must be configured according to your email service provider.
For Gmail, set MAIL_USERNAME to your Gmail address and MAIL_PASSWORD to an app password generated via your Google account.
Reference: https://every-up.tistory.com/81
##3.	Build and Run with Docker
1.	Open a terminal and navigate to the root CoDeF folder.
2.	Build the Docker image: 

docker build -t codef .
3.	
4.	Run the application in detached mode:
Docker-compose up –d
##4.	Accessing the Web Application
Open your browser and enter the domain specified in .env.prod..
Ex) http://localhost:8000
