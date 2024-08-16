import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.timezone import localtime
from django.views.generic.edit import FormView

from control.models import ControlRecord
from kurasel_translator.forms import MonthlyBalanceForm
from kurasel_translator.my_lib import append_list, check_lib
from kurasel_translator.my_lib.append_list import select_period
from monthly_report.models import ReportTransaction
from record.models import AccountingClass, Himoku

logger = logging.getLogger(__name__)


class MonthlyBalanceView(PermissionRequiredMixin, FormView):
    """月次収支データの取り込み
    - 年月を指定して取り込む。
    - 取り込みはget_or_create()を使う。
    """

    # テンプレート名の設定
    template_name = "kurasel_translator/monthlybalance_form.html"
    # フォームの設定
    form_class = MonthlyBalanceForm
    permission_required = "record.add_transaction"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 年月既定値
        form = MonthlyBalanceForm(
            initial={
                "year": localtime(timezone.now()).year,
                "month": localtime(timezone.now()).month,
            }
        )
        context["form"] = form
        return context

    def form_valid(self, form):
        year = form.cleaned_data["year"]
        month = form.cleaned_data["month"]
        accounting_class = form.cleaned_data["accounting_class"]
        kind = form.cleaned_data["kind"]
        mode = form.cleaned_data["mode"]
        note = form.cleaned_data["note"]

        context = {
            "form": form,
            "year": year,
            "month": month,
            "kind": kind,
            "mode": mode,
            "author": self.request.user.pk,
        }
        # msgを’\r\n'で区切ってリストを作成する。
        tmp_list = note.splitlines()
        # tmp_listから空の要素を削除する。
        msg_list = [a for a in tmp_list if a != ""]
        # (1) msg_listがKurasel月次収支データのヘッダを正しくコピーしているかをチェック。
        err_msg = check_lib.check_copy_area(msg_list)
        if err_msg:
            messages.add_message(self.request, messages.ERROR, err_msg)
            return render(self.request, self.template_name, context)
        # ヘッダから「収入」「支出」を判断した後、不要なヘッダ部分を除去する。
        data_kind, msg_list = check_lib.check_data_kind(msg_list)
        # (2) 収支区分（収入・支出）のチェック
        if data_kind != kind:
            err_msg = "「収支区分」がデータと一致していません！"
            messages.add_message(self.request, messages.ERROR, err_msg)
            return render(self.request, self.template_name, context)

        # msg_listデータを5行で1レコードのListに変換する。
        data_list = self.translate(msg_list, 5)

        # 会計区分をチェックする。
        chk = check_lib.check_accountingclass(data_list, str(accounting_class))
        if chk is False:
            msg = "「会計区分」を確認してください。"
            messages.add_message(self.request, messages.ERROR, msg)

        # -------------------------------------------------------------
        # 管理組合会計の場合、無効な町内会関係の費目を除外する
        # -------------------------------------------------------------
        if str(accounting_class) != settings.COMMUNITY_ACCOUNTING:
            himoku_qs = Himoku.get_without_community()
            test_list = []
            for data in data_list:
                for himoku in himoku_qs:
                    if data[0] == himoku.himoku_name:
                        test_list.append(data)
                        break
            data_list = test_list

        # チェックと正規化したdata_listをcontextに追加。
        context["data_list"] = data_list
        if "確認" in mode:
            # 合計を計算
            total = 0
            for data in data_list:
                total += int(data[2])
            context["total"] = total
            # 確認モードの場合、表示のみを行う。
            return render(self.request, self.template_name, context)
        else:
            # 登録モードの場合、ReportTransactionモデルクラス関数でデータ保存する
            rtn, error_list = ReportTransaction.monthly_from_kurasel(
                accounting_class, context
            )
            # 相殺処理の費目が設定されている場合、相殺フラグのセットを行う。
            offset_himoku = ControlRecord.get_offset_himoku()
            if offset_himoku:
                tstart, tend = select_period(year, month)
                ReportTransaction.set_offset_flag(offset_himoku, tstart, tend)
            # データ取込みが成功した場合の戻り処理を行う。
            if rtn:
                msg = "月次収支データの取り込みが完了しました。"
                messages.add_message(self.request, messages.ERROR, msg)
                # 保存成功後に遷移する場合のパラメータ。受け取りはkwargs.get["year"]とする。
                ac_pk = AccountingClass.objects.get(accounting_name=accounting_class).pk
                param = dict(year=year, month=str(month).zfill(2), ac_class=ac_pk)
                # 取り込みに成功したら、一覧表表示する。
                if kind == "収入":
                    # 収入データの取り込みに成功したら、一覧表表示する。
                    url = append_list.redirect_with_param(
                        "monthly_report:incomelist", param
                    )
                    return redirect(url)
                else:
                    # 支出データの取り込みに成功したら、一覧表表示する。
                    url = append_list.redirect_with_param(
                        "monthly_report:expenselist", param
                    )
                    return redirect(url)
            else:
                # msg = f'月次収支データの取り込みに失敗しました。費目名 ＝ {error_list[0]}'
                for i in error_list:
                    msg = f"月次収支データの取り込みに失敗しました。{i}"
                    messages.add_message(self.request, messages.ERROR, msg)
                # 取り込みに失敗したら、取り込み画面に戻る。
                return render(self.request, self.template_name, context)

    def translate(self, msg_list, row):
        """Kuraselの表示をコピペで取り込む
        - "¥"マーク、"（円）"、","の3つを削除。
        - strip()は最後に行う。
        """
        cnt = 0
        record_list = []
        line_list = []
        for line in msg_list:
            line_list.append(
                line.replace("¥", "").replace("（円）", "").replace(",", "").strip()
            )
            cnt += 1
            if cnt == row:
                record_list.append(line_list)
                cnt = 0
                line_list = []
        return record_list