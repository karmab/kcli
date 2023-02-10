function poolcreate(){
  $("#wheel").show();
  var pool = $("#pool").val();
  var path = $("#path").val();
  var type = $("#type").val();
  data = {'pool': pool, 'path': path, 'type': type};
  $.ajax({
       type: "POST",
        url: '/pools',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Pool "+pool+" created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Pool "+pool+" not created because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function pooldelete(pool){
  $("#wheel").show();
  $.ajax({
       type: "DELETE",
        url: `/pools/${pool}`,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Pool "+pool+" deleted!!!" }, type: 'success'}).show();
                poolstable();
            } else {
                $('.top-right').notify({message: { text: "Pool "+pool+" not created because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}
