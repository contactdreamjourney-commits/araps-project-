#!/usr/bin/env bash
gunicorn result_system.wsgi:application