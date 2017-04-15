function networkcreate(){
  $("#wheel").show();
  var network = $("#network").val();
  var cidr = $("#cidr").val();
  var isolated = $("#isolated").val();
  var dhcp = $("#dhcp").val();
  data = {'network': network, 'cidr': cidr, 'dhcp': dhcp, 'isolated': isolated, 'action': 'create'};
  $.ajax({
       type: "POST",
        url: '/networkaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Network "+network+" Created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Network "+network+" Failed to Create Because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function networkdelete(network){
  $("#wheel").show();
  data = {'network': network, 'action': 'delete'};
  $.ajax({
       type: "POST",
        url: '/networkaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Network "+network+" Deleted!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Network "+network+" Deleted to Create Because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}
