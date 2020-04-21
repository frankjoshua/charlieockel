#!/bin/bash

touch images.html
echo "" > images.html
for IMAGE in images/*
do
BASE_IMAGE=$(basename "${IMAGE}")
echo "<a href=\"${IMAGE}\">${BASE_IMAGE}</a>" >> images.html
done