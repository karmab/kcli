function productcreate(product){
  var plan = prompt("Enter plan name or leave blank to autogenerate one");
  $("#wheel").show();
  data = {'plan': plan, 'action': 'create', 'product': product};
  $.ajax({
       type: "POST",
        url: '/productaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                plan = data.plan
                $('.top-right').notify({message: { text: "Plan "+plan+" created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Plan "+plan+" not created because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}
