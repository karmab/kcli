function exposedelete(plan){
  $("#wheel").show();
  var r = confirm("Are you sure you want to delete this Plan?");
  if (r != true) {
    $("#wheel").hide();
    return ;
  }
  $.ajax({
       type: "DELETE",
        url: `/expose/${plan}`,
        success: function(data) {
            $("#wheel").hide();
                location.reload(true);
        }
    });
}
