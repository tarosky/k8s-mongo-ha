// This code initializes MongoDB replica set.
serverHost = '%HOST%';

// This function assumes the host name (and optional port) format is like
// "mongo-0.mongo.default.svc.cluster.local:27017".
hostNo = function(host) {
  var words = host.split(':')[0].split('.')[0].split('-');
  return parseInt(words[words.length - 1]);
};

service = serverHost.split('.')[1];

if (!service) {
  print('Illegal service host');
  quit(1);
}

status = rs.status();
if (status.codeName === 'NotYetInitialized') {
  var no = hostNo(serverHost);
  rs.initiate({
    _id: service,
    members: [{
      _id: no,
      host: serverHost,
      priority: 1000 - no,
    }],
  });
  print('Mongo has been initialized: host: ' + serverHost);
} else {
  printjson(status);
  print('Already initialized; nothing has been done.');
  quit(1);
}
