// This code does several tasks:
//   - check initialization status of this node
//   - validate the current replica set status if this is the primary node
//   - scale out/in if this is the primary node and it is required

PRIMARY = 1;

serverHost = '%HOST%';
hostCount = parseInt('%HOST_COUNT%');

// This function returns the host name and port specified by host number.
hostByNo = function(no) {
  var items = serverHost.split('.');
  var words = items[0].split('-');
  var newHost = words.slice(0, -1).concat(no.toString()).join('-');
  return [newHost].concat(items.slice(1)).join('.') + ':27017';
};

// This function extracts the host number from host name (and optional port).
hostNo = function(host) {
  var words = host.split(':')[0].split('.')[0].split('-');
  return parseInt(words[words.length - 1]);
};

scaleOut = function(from, to) {
  for (var i = from; i < to; i++) {
    rs.add({
      _id: i,
      host: hostByNo(i),
      // This priority keeps smaller node primary, which makes scale-in safer.
      priority: 1000 - i,
    });
  }

  printjson(rs.status());
  print('Scale Out has been executed.');
};

scaleIn = function(from, to) {
  for (var i = from - 1; to <= i; i--) {
    rs.remove(hostByNo(i));
  }

  printjson(rs.status());
  print('Scale In has been executed.');
};

// This validation keeps status of replica set less complicated.
validate = function(status) {
  for (var i = 0; i < status.members.length; i++) {
    var member = status.members[i];
    if (member._id !== i || member._id !== hostNo(member.name)) {
      return false;
    }
  }
  return true;
};

run = function() {
  status = rs.status();
  if (status.codeName === 'NotYetInitialized') {
    print('__NOT_INITIALIZED__');
    return;
  }

  if (status.myState !== PRIMARY) {
    return;
  }

  if (!validate(status)) {
    printjson(status);
    print('__INVALID_STATUS__');
    return;
  }

  if (status.members.length < hostCount) {
    scaleOut(status.members.length, hostCount);
  } else if (hostCount < status.members.length) {
    scaleIn(status.members.length, hostCount);
  }
};

run();
