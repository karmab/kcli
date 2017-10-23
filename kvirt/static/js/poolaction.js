function poolcreate(){
  $("#wheel").show();
  var pool = $("#pool").val();
  var path = $("#path").val();
  var type = $("#type").val();
  data = {'pool': pool, 'path': path, 'type': type, 'action': 'create'};
  $.ajax({
       type: "POST",
        url: '/poolaction',
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
  data = {'pool': pool, 'action': 'delete'};
  $.ajax({
       type: "POST",
        url: '/poolaction',
        data: data,
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
