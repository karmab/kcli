function productcreate(){
  $("#wheel").show();
  var product = $("#product").val();
  var plan = $("#plan").val();
  var parameters = {};
  $.each($('#createproduct').serializeArray(), function() {
    parameters[this.name] = this.value;
  });
  data = {'action': 'create', 'product': product, 'plan': plan, 'parameters': parameters};
  $.ajax({
       type: "POST",
        url: '/productaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                plan = data.plan
                $('.top-right').notify({message: { text: "Product "+plan+" created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Product "+plan+" not created because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}
