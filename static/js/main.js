
function TreeMap(data){
  this.data = data;
  return this;
};

TreeMap.prototype.draw = function() {

  var headers = [
  ['Region', 'Parent', 'Instances', 'Instances'],
  ['Global', null, 0, 0],
  ]

  var dataTable = google.visualization.arrayToDataTable(headers.concat(this.data))

  tree = new google.visualization.TreeMap(document.getElementById('treemap'));
  tree.draw(dataTable, {
    minColor: '#f00',
    midColor: '#ddd',
    maxColor: '#0d0',
    headerHeight: 15,
    fontColor: 'black',
    showScale: true
  });
};

function RecentGauges(recent, total, queued){
  this.recent = recent;
  this.total = total;
  this.queued = queued;
  return this;
};

RecentGauges.prototype.draw = function() {
  var data = google.visualization.arrayToDataTable([
    ['Label', 'Value'],
    ['Recent', this.recent],
    ['Total', this.total],
    ['Queued', this.queued]
  ]);
  var chart = new google.visualization.Gauge(document.getElementById('recent-gauges'));
  var options = {
    minorTicks: 5
  };
  chart.draw(data, options);
};

function HomogenyGauge(data){
  this.data = data;
  return this;
};

HomogenyGauge.prototype.draw = function() {
  var headers = [['AMI_ID', 'Count'],]

  var dataTable = google.visualization.arrayToDataTable(headers.concat(this.data))

  var options = {
    pieHole: 0.4,
  };

  var chart = new google.visualization.PieChart(document.getElementById('homogenychart'));
  chart.draw(dataTable, options);
};

function Advise(data){
  this.data = data;
  return this;
}

Advise.prototype.render = function() {
  for(var category_name in this.data.results){
    var general = this.findGeneralFailures(this.data.results[category_name].generals)
    var collection = this.findCollectionFailures(this.data.results[category_name].collections)

    var category = {
      category_name: category_name,
      collections: collection.report,
      collection_stats: collection.stats,
      generals: general.report,
      general_stats: general.stats,
      total_failures: general.stats.failure_count + collection.stats.failure_count
    }

    this.data.results[category_name]
    category['category_name'] = category_name;
    html = $.mustache('advise/_advise.mustache', category);
    $('.advise').append(html);

  }
  $('.advise__category-head').click(function() {
    $(this).parent().toggleClass('expand-category');
  });
  $('.advise__category-section_name').click(function() {
    $(this).parent().toggleClass('expand-section');
  });
}

Advise.prototype.findGeneralFailures = function(data) {
  var total_count = data.length
  var failures = data.filter(function(check){
    return check.status == "FAIL"
  });
  var failure_count = failures.length
  return {stats: {total_count: total_count, failure_count: failure_count}, report: data}
}

Advise.prototype.findCollectionFailures = function(data) {
  var resource_count = data.length

  var failures = data.filter(function(check){
    return check.status == "FAIL"
  });
  var failure_count = failures.length
  return {stats: {resource_count: resource_count, failure_count: failure_count}, report: failures}
}



