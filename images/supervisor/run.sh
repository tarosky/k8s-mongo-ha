#!/bin/bash

set -eu

if [ "$DEBUG" == 'true' ]; then
  set -x
fi

readonly namespace="$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)"
readonly service_domain="_$SERVICE_PORT._tcp.$SERVICE.$namespace.svc.cluster.local"
readonly head_domain_pattern="-0.$SERVICE.$namespace.svc.cluster.local"

run_mongo_task () {
  local -r s="$1"
  local -r count="$2"

  < /task.template.js sed "s/%HOST%/$s/g" | \
    sed "s/%HOST_COUNT%/$count/g" > /task.js

  set +e
  timeout 10 mongo --quiet --host "$s" /task.js
  set -e
}

run_mongo_init () {
  local -r s="$1"

  < /init.template.js sed "s/%HOST%/$s/g" > /init.js

  set +e
  timeout 10 mongo --quiet --host "$s" /init.js
  set -e
}

server_domains () {
  dig +noall +answer srv "$1" | awk -F' ' '{print $NF}' | sed 's/\.$//g'
}

# This function extracts the host number from host name.
statefulset_suffix () {
  echo "$1" | cut -d'.' -f1 | sed 's/.\+-\([0-9]\+\)$/\1/g'
}

max_suffix () {
  local count="-1"
  for s in $1; do
    local suffix
    suffix="$(statefulset_suffix "$s")"
    if [ "$count" -lt "$suffix" ]; then
      count="$suffix"
    fi
  done

  local -r wc_count="$(echo "$1" | grep -c 'svc.cluster.local')"
  local -r suffix_count="$((count + 1))"
  # If the two values are different, it is in a exceptional state.
  # Wait for the state to be steady by exiting.
  # Exit with an error code to tell the sys admin what happens.
  if [ "$wc_count" -ne "$suffix_count" ]; then
    >&2 echo "$1"
    >&2 echo 'Error: Server count does not match.'
    exit 1
  fi

  echo "$suffix_count"
}

initialized () {
  ! echo "$1" | grep -e '^__NOT_INITIALIZED__$' > /dev/null
}

invalid_status () {
  echo "$1" | grep -e '^__INVALID_STATUS__$' > /dev/null
}

main () {
  local -r servers="$(server_domains "$service_domain")"
  local -r count="$(max_suffix "$servers")"

  local require_init='true'
  if [ "$count" -eq '0' ]; then
    require_init='false'
  fi

  local s
  for s in $servers; do
    local i
    i="$(run_mongo_task "$s" "$count")"
    if initialized "$i"; then
      require_init='false'
    fi
    if invalid_status "$i"; then
      return 1
    fi
  done

  # Initialization should be done only when all the nodes are uninitialized
  # and the head node exists.
  if [ "$require_init" = 'true' ]; then
    local -r head_domain="$(echo "$servers" | grep -- "$head_domain_pattern")"
    if [ -n "$head_domain" ]; then
      run_mongo_init "$head_domain"
    fi
  fi
}

while true; do
  sleep 60
  main
done
