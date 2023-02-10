function networkcreate(){
  $("#wheel").show();
  var network = $("#network").val();
  var cidr = $("#cidr").val();
  var isolated = $("#isolated").val();
  var dhcp = $("#dhcp").val();
  data = {'network': network, 'cidr': cidr, 'dhcp': dhcp, 'isolated': isolated};
  $.ajax({
       type: "POST",
        url: '/networks',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Network "+network+" created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Network "+network+" not created because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function networkdelete(network){
  $("#wheel").show();
  $.ajax({
       type: "DELETE",
        url: `/networks/${network}`,
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Network "+network+" Deleted!!!" }, type: 'success'}).show();
                networkstable();
            } else {
                $('.top-right').notify({message: { text: "Network "+network+" not deleted :because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}
