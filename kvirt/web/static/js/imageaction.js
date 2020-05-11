function imagecreate(image, pool, url, cmd){
  if ( image === undefined ) {
    image = $("#image").val();
  }
  if ( pool === undefined ) {
    pool = $("#pool").val();
  }
  if ( url === undefined ) {
    url = $("#url").val();
  }
  if ( cmd === undefined ) {
    cmd = $("#cmd").val();
  }
  $("#wheel").show();
  data = {'image': image, 'action': 'create', 'pool': pool, 'url': url, 'cmd': cmd};
  $.ajax({
       type: "POST",
        url: '/imageaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            $("#urllabel").hide();
            $("#url").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Image "+image+" created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Image "+image+" not created because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function imageurl(){
    image = $( "#image option:selected" ).text();
    if (~image.indexOf("rhel")) {
    $("#url").show();
    $("#urllabel").show();
    url = $( "#image option:selected" ).attr("url");
    window.open(url, "_blank");
    }
}
