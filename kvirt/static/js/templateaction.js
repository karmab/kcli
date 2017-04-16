function templatecreate(template, pool){
  $("#wheel").show();
  data = {'template': template, 'action': 'create', 'pool': pool};
  $.ajax({
       type: "POST",
        url: '/templateaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Template "+template+" Created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Template "+template+" Failed to Create Because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}
