function repocreate(){
  $("#wheel").show();
  var repo = $("#repo").val();
  var url = $("#URL").val();
  data = {'repo': repo, 'url': url};
  $.ajax({
       type: "POST",
        url: '/repos',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Repo "+repo+" created!!!" }, type: 'success'}).show();
                repostable();
            } else {
                $('.top-right').notify({message: { text: "Repo "+repo+" not created Because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function repodelete(repo){
  $("#wheel").show();
  data = {'repo': repo};
  $.ajax({
       type: "DELETE",
        url: `/repos/${repo}`,
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Repo "+repo+" deleted!!!" }, type: 'success'}).show();
                repostable();
            } else {
                $('.top-right').notify({message: { text: "Repo "+repo+" not deleted Because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function repoupdate(repo){
  $("#wheel").show();
  data = {'repo': repo};
  $.ajax({
       type: "PATCH",
        url: `/repos/${repo}`,
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Repo "+repo+" updated!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Repo "+repo+" not updated Because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}
