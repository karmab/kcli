function templatecreate(template, pool, url){
  $("#wheel").show();
  data = {'template': template, 'action': 'create', 'pool': pool, 'url': url};
  $.ajax({
       type: "POST",
        url: '/templateaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            $("#urllabel").hide();
            $("#url").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Template "+template+" Created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Template "+template+" Failed to Create Because "+data.reason }, type: 'danger'}).show();
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
