/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.imagecat.workflow;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Creates the workflow instance tables when they are not there, and does
 * nothing at all when they are.
 *
 * <p>The workflow instance repository is a database, and ImageCat has no
 * step that creates it beyond a hand-run one. That is survivable right up
 * until someone clears {@code data/} between runs, which is a normal thing to
 * do and which is how this was found. HSQLDB then creates a fresh, empty
 * database on the next connection, and the Workflow Manager starts perfectly
 * cleanly: it binds its port, loads its policy, lists its five workflows and
 * registers its events. Every one of those health checks passes, and every
 * workflow start fails:
 *
 * <pre>
 *   ERROR AvroRpcWorkflowManager - Error when starting workflow:
 *         ExtractStringsWorkflow with metadata: []
 *   EngineException: user lacks privilege or object not found:
 *         WORKFLOW_INSTANCES in statement [INSERT INTO workflow_instances ...]
 * </pre>
 *
 * <p>The manager says exactly what is wrong. What it cannot do is fix it, and
 * nothing else was going to either. This is run from {@code bin/oodt} before
 * the Workflow Manager is launched, rather than only from setup, because setup
 * is exactly what does not get re-run in that situation.
 *
 * <p>It is deliberately narrow. If the instance repository is not the
 * datasource-backed one, or the tables already exist, it exits without
 * touching anything.
 */
/*
 * Copied from BigTranslate, which has run this against a 458-chunk job. It is
 * generic OODT plumbing with nothing project-specific in it, and it is
 * duplicated rather than shared because it lives in an application repo
 * instead of Mnemosyne. Promote it to Mnemosyne and delete both copies.
 */
public class WorkflowInstanceSchema {

  static final String REPO_FACTORY_KEY =
      "workflow.engine.instanceRep.factory";
  static final String DATASOURCE_FACTORY =
      "org.apache.oodt.cas.workflow.instrepo."
          + "DataSourceWorkflowInstanceRepositoryFactory";

  static final String URL_KEY =
      "org.apache.oodt.cas.workflow.instanceRep.datasource.jdbc.url";
  static final String USER_KEY =
      "org.apache.oodt.cas.workflow.instanceRep.datasource.jdbc.user";
  static final String PASS_KEY =
      "org.apache.oodt.cas.workflow.instanceRep.datasource.jdbc.pass";
  static final String DRIVER_KEY =
      "org.apache.oodt.cas.workflow.instanceRep.datasource.jdbc.driver";

  static final String SENTINEL_TABLE = "workflow_instances";

  private static final Pattern PLACEHOLDER =
      Pattern.compile("\\[([A-Za-z_][A-Za-z0-9_]*)\\]");

  /**
   * @param args workflow.properties, then the .sql file to apply
   */
  public static void main(String[] args) throws Exception {
    if (args.length < 2) {
      System.err.println("usage: WorkflowInstanceSchema "
          + "<workflow.properties> <workflow-instances.sql>");
      System.exit(2);
    }
    System.exit(ensure(new File(args[0]), new File(args[1])) ? 0 : 1);
  }

  static boolean ensure(File propertiesFile, File sqlFile) {
    try {
      Properties properties = load(propertiesFile);

      String factory = properties.getProperty(REPO_FACTORY_KEY);
      if (factory == null || !factory.trim().equals(DATASOURCE_FACTORY)) {
        // A Lucene-backed repository, or none configured. Nothing to create.
        return true;
      }

      String url = resolve(properties.getProperty(URL_KEY));
      if (url == null) {
        System.err.println("No [" + URL_KEY + "] in " + propertiesFile
            + "; leaving the workflow instance database alone");
        return false;
      }
      // A placeholder that nothing in the environment answers is not a path.
      // HSQLDB will happily open jdbc:hsqldb:file:[OODT_HOME]/data/winstdb --
      // creating a directory literally named "[OODT_HOME]" beside wherever
      // this was run from -- and every line after here then reports success
      // for a database the Workflow Manager will never look at. Refuse, and
      // say which variable is missing.
      Matcher unresolved = PLACEHOLDER.matcher(url);
      if (unresolved.find()) {
        System.err.println("The instance database URL still contains "
            + unresolved.group(0) + " after resolution: " + url);
        System.err.println("Set and export " + unresolved.group(1)
            + " before running this; bin/oodt does it through bin/env.sh.");
        return false;
      }
      String driver = properties.getProperty(DRIVER_KEY);
      if (driver != null && driver.trim().length() > 0) {
        Class.forName(driver.trim());
      }
      String user = value(properties.getProperty(USER_KEY), "sa");
      String pass = value(properties.getProperty(PASS_KEY), "");

      Connection connection = DriverManager.getConnection(url, user, pass);
      try {
        if (hasTable(connection, SENTINEL_TABLE)) {
          return true;
        }
        System.out.println("Creating the workflow instance tables in " + url);
        Statement statement = connection.createStatement();
        try {
          for (String each : statements(sqlFile)) {
            statement.execute(each);
          }
        } finally {
          statement.close();
        }
        System.out.println("Workflow instance tables created");
        return true;
      } finally {
        shutdownAndClose(connection, url);
      }
    } catch (Exception e) {
      // Reported rather than thrown: the caller warns and carries on, because
      // a Workflow Manager that will not start is worse than one that starts
      // and complains.
      System.err.println("Could not check the workflow instance database: "
          + e);
      return false;
    }
  }

  /**
   * HSQLDB in file mode holds the database open in this process and takes a
   * lock with it. Without an explicit SHUTDOWN the DDL sits in the .log and
   * the lock file is left behind, and the Workflow Manager we are about to
   * start finds the database still locked.
   */
  private static void shutdownAndClose(Connection connection, String url) {
    try {
      if (url.startsWith("jdbc:hsqldb:file:")) {
        Statement statement = connection.createStatement();
        try {
          statement.execute("SHUTDOWN");
        } finally {
          statement.close();
        }
      }
    } catch (Exception e) {
      System.err.println("Could not shut the database down cleanly: " + e);
    } finally {
      try {
        connection.close();
      } catch (Exception ignored) {
        // Already going away.
      }
    }
  }

  static boolean hasTable(Connection connection, String table)
      throws Exception {
    DatabaseMetaData metaData = connection.getMetaData();
    // Asked three ways because the case a database stores an unquoted
    // identifier in is its own business: HSQLDB folds to upper case, others
    // fold to lower.
    String[] spellings = new String[] {
        table, table.toUpperCase(), table.toLowerCase()};
    for (String spelling : spellings) {
      ResultSet tables = metaData.getTables(null, null, spelling, null);
      try {
        if (tables.next()) {
          return true;
        }
      } finally {
        tables.close();
      }
    }
    return false;
  }

  /**
   * The statements in a .sql file, with comments removed. A trailing comment
   * after the last semicolon otherwise arrives as a statement of its own.
   */
  static List<String> statements(File sqlFile) throws Exception {
    StringBuilder builder = new StringBuilder();
    Reader reader = new InputStreamReader(new FileInputStream(sqlFile),
        StandardCharsets.UTF_8);
    try {
      char[] buffer = new char[8192];
      int read;
      while ((read = reader.read(buffer)) != -1) {
        builder.append(buffer, 0, read);
      }
    } finally {
      reader.close();
    }

    StringBuilder stripped = new StringBuilder();
    for (String line : builder.toString().split("\n")) {
      int comment = line.indexOf("--");
      stripped.append(comment >= 0 ? line.substring(0, comment) : line);
      stripped.append("\n");
    }

    List<String> statements = new ArrayList<String>();
    for (String each : stripped.toString().split(";")) {
      if (each.trim().length() > 0) {
        statements.add(each);
      }
    }
    return statements;
  }

  /**
   * Substitutes {@code [NAME]} from the environment, the same shape of
   * placeholder the OODT policy files use.
   */
  static String resolve(String raw) {
    if (raw == null) {
      return null;
    }
    Matcher matcher = PLACEHOLDER.matcher(raw);
    StringBuffer out = new StringBuffer();
    while (matcher.find()) {
      String replacement = System.getenv(matcher.group(1));
      matcher.appendReplacement(out, Matcher.quoteReplacement(
          replacement != null ? replacement : matcher.group(0)));
    }
    matcher.appendTail(out);
    return out.toString();
  }

  private static String value(String raw, String fallback) {
    return raw != null ? raw : fallback;
  }

  private static Properties load(File file) throws Exception {
    Properties properties = new Properties();
    InputStream in = new FileInputStream(file);
    try {
      properties.load(in);
    } finally {
      in.close();
    }
    return properties;
  }
}
