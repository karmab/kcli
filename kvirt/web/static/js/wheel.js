$(document).ajaxStart(function() {
  $("#wheel").show();
});


$(document).ajaxStop(function() {
  $("#wheel").hide();
});
