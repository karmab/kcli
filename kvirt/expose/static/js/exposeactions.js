function exposedelete(plan){
  $("#wheel").show();
  data = {'plan': plan};
  var r = confirm("Are you sure you want to delete this Plan?");
  if (r != true) {
    return ;
  }
  $.ajax({
       type: "POST",
        url: '/exposedelete',
        data: data,
        success: function(data) {
            $("#wheel").hide();
                location.reload(true);
        }
    });
}
