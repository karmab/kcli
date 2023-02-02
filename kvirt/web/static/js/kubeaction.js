function kubecreate(){
  $("#wheel").show();
  var type = $("#type").val();
  var parameters = {};
  $.each($('#createkube').serializeArray(), function() {
    parameters[this.name] = this.value;
  });
  data = {'type': type, 'parameters': parameters};
  cluster = parameters['cluster'];
  $.ajax({
       type: "POST",
        url: '/kubecreate',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Cluster "+cluster+" created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Cluster "+cluster+" not created because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}
