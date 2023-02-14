$(document).ready(function() {
 setInterval(function(){
 var refresh = $("#refresh");
 if (refresh.prop("checked")) {
    location.reload();
    refresh.prop("checked", true)
  } else {
    refresh.prop("checked", false)
  }
},10000);
$.ajaxSetup({ cache: false });
});
