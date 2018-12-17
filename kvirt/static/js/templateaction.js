function templatecreate(template, pool, url, cmd){
  $("#wheel").show();
  data = {'template': template, 'action': 'create', 'pool': pool, 'url': url, 'cmd': cmd};
  $.ajax({
       type: "POST",
        url: '/templateaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            $("#urllabel").hide();
            $("#url").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Template "+template+" created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Template "+template+" not created because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function templateurl(){
    template = $( "#template option:selected" ).text();
    if (~template.indexOf("rhel")) {
    $("#url").show();
    $("#urllabel").show();
    url = $( "#template option:selected" ).attr("url");
    window.open(url, "_blank");
    }
}

function templatecreate2(){
var template = $("#template").val();
var pool = $("#pool").val();
var url = $("#url").val();
var cmd = $("#cmd").val();
templatecreate(template, pool, url, cmd);
}
