#!/bin/bash
docker build -f Dockerfile_opsapi_test_suite -t opsapi_test_suite . --no-cache 
docker run opsapi_test_suite