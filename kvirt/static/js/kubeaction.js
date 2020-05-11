function kubecreate(){
  $("#wheel").show();
  var cluster = $("#cluster").val();
  var type = $("#type").val();
  var parameters = {};
  $.each($('#createkube').serializeArray(), function() {
    parameters[this.name] = this.value;
  });
  data = {'action': 'create', 'type': type, 'cluster': cluster, 'parameters': parameters};
  $.ajax({
       type: "POST",
        url: '/kubeaction',
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
