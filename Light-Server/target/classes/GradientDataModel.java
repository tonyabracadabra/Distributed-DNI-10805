import io.undertow.Undertow;
import io.undertow.server.HttpHandler;
import io.undertow.server.HttpServerExchange;
import io.undertow.util.Headers;

import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

import java.util.*;

public class GradientDataModel {
    // Instance variables
    private List<Connection> connectionPool = new ArrayList<Connection>();
    private final String JDBC_DRIVER = "com.mysql.jdbc.Driver";
    private final String DB_NAME = "test";
    private final String JDBC_URL = "jdbc:mysql://localhost/" + DB_NAME + "?useSSL=false";
    private String tableName;

    /**
     * Constructor
     */
    public GradientDataModel(String tableName) throws Exception {
        // Create table if not exists
        this.tableName = tableName;
        createTable();
    }

    /**
     * Drop all items
     */
    public void dropAllItems() throws Exception {
        Connection con = null;
        PreparedStatement pstmt = null;
        try {
            con = getConnection();
            con.setAutoCommit(false);
            
            pstmt = con.prepareStatement("DELETE FROM " + tableName + ";");

            pstmt.executeUpdate();

            pstmt.close();
            
            con.commit();
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            if (pstmt != null) {
                try {
                    pstmt.close();
                } catch (SQLException e) {
                    e.printStackTrace();
                }
            }
            if (con != null) {
                con.setAutoCommit(true);
                releaseConnection(con);
            }
        }
    }
    

    /**
     * Connect to MySQL Server
     */ 
    public synchronized Connection getConnection() throws Exception {
        if (connectionPool.size() > 0) {
            return connectionPool.remove(connectionPool.size() - 1);
        }

        try {
            Class.forName(JDBC_DRIVER);
        } catch (Exception e) {
            e.printStackTrace();
        }

        try {
            return DriverManager.getConnection(JDBC_URL);
        } catch (Exception e) {
            e.printStackTrace();
        }

        return null;
    }

    /** 
     * Release connection
     */
    public synchronized void releaseConnection(Connection con) {
        connectionPool.add(con);
    }

    /**
     * Insert new record using transaction
     */
    public void insert(int level, int iteration, String true_gradient) throws Exception {
        Connection con = null;
        PreparedStatement pstmt = null;
        Statement stmt = null;

        try {
            con = getConnection();
            con.setAutoCommit(false);

            // Get count
            stmt = con.createStatement();
            ResultSet rs = stmt.executeQuery("SELECT COUNT(*) AS count FROM " + tableName + " WHERE level = " + level + ";");
            int count = 0;
            if (rs != null) {
                while (rs.next()) {
                    count = rs.getInt("count");
                }
            }
            System.out.println("[Gradient][INSERT][BEFORE INSERT] remains: " + count);

            
            pstmt = con.prepareStatement("INSERT INTO " + tableName + 
                                         " (level, iteration, true_gradient) VALUES(?, ?, ?);");

            System.out.println("[Gradient][INSERT]iteration: " + iteration + "\tlength: " + true_gradient.length());

            pstmt.setInt(1, level);
            pstmt.setInt(2, iteration);
            pstmt.setString(3, true_gradient);

            pstmt.executeUpdate();

            // Get count
            rs = stmt.executeQuery("SELECT COUNT(*) AS count FROM " + tableName + " WHERE level = " + level + ";");
            count = 0;
            if (rs != null) {
                while (rs.next()) {
                    count = rs.getInt("count");
                }
            }
            System.out.println("[Gradient][INSERT][BEFORE INSERT] remains: " + count);

            pstmt.close();
            
            con.commit();
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            if (pstmt != null) {
                try {
                    pstmt.close();
                } catch (SQLException e) {
                    e.printStackTrace();
                }
            }
            if (con != null) {
                con.setAutoCommit(true);
                releaseConnection(con);
            }
        }
    }


    /**
     * Get new record
     */
    public String get(int level) throws Exception {
        Connection con = null;
        Statement stmt = null;
        PreparedStatement pstmt = null;
        String res = "";
        int iteration = -1;

        try {
            con = getConnection();
            con.setAutoCommit(false);

            stmt = con.createStatement();
            ResultSet rs = stmt.executeQuery("SELECT * FROM " + tableName + 
                " WHERE level = " + level + " GROUP BY level, iteration, true_gradient, timestamp" + 
                " ORDER BY timestamp ASC, iteration ASC LIMIT 1;");

            // If not null, get the result and delete the oldest one
            if (rs != null) {
                while (rs.next()) {
                    res = rs.getString("true_gradient");
                    iteration = rs.getInt("iteration");
                }
                res += "\t" + iteration;
                System.out.println("[Gradient][GET]iteration: " + iteration + "\tlength: " + res.length());

                // Get count
                rs = stmt.executeQuery("SELECT COUNT(*) AS count FROM " + tableName + " WHERE level = " + level + ";");
                int count = 0;
                if (rs != null) {
                    while (rs.next()) {
                        count = rs.getInt("count");
                    }
                }
                System.out.println("[Gradient][GET][BEFORE DELETE] remains: " + count);

                if (iteration != -1) {
                    pstmt = con.prepareStatement("DELETE FROM " + tableName + " WHERE level = " + level + 
                                             " AND iteration = " + iteration + ";");

                    pstmt.executeUpdate();

                    pstmt.close();

                    System.out.println("[Gradient][DELETE] level: " + level + "\titeration: " + iteration);

                    // Get count
                    rs = stmt.executeQuery("SELECT COUNT(*) AS count FROM " + tableName + " WHERE level = " + level + ";");
                    count = 0;
                    if (rs != null) {
                        while (rs.next()) {
                            count = rs.getInt("count");
                        }
                    }
                    System.out.println("[Gradient][GET][AFTER DELETE] remains: " + count);
                }
            }

            stmt.close();
            
            con.commit();
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            if (pstmt != null) {
                try {
                    pstmt.close();
                } catch (SQLException e) {
                    e.printStackTrace();
                }
            }
            if (stmt != null) {
                try {
                    stmt.close();
                } catch (SQLException e) {
                    e.printStackTrace();
                }
            }
            if (con != null) {
                con.setAutoCommit(true);
                releaseConnection(con);
            }

            return res;
        }
    }


    /**
     * Create Index on column
     */
    public void createIndex(String columnName) throws Exception {
        Connection con = null;
        Statement stmt = null;
        String indexName = columnName + "_index";

        try {
            con = getConnection();
            con.setAutoCommit(false);
            
            stmt = con.createStatement();
            stmt.executeUpdate("CREATE INDEX " + indexName + " ON " + tableName + " (" + columnName + ");"
            );
            stmt.close();
            
            con.commit();
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            if (stmt != null) {
                try {
                    stmt.close();
                } catch (SQLException e) {
                    e.printStackTrace();
                }
            }
            if (con != null) {
                con.setAutoCommit(true);
                releaseConnection(con);
            }
        }
    }


    /**
     * Create table if not exists using transaction
     */
    public void createTable() throws Exception {
        Connection con = null;
        Statement stmt = null;
        try {
            con = getConnection();
            con.setAutoCommit(false);
            
            stmt = con.createStatement();
            stmt.executeUpdate("CREATE TABLE IF NOT EXISTS " + tableName + 
                " (level INT NOT NULL, iteration INT NOT NULL, true_gradient TEXT, " +
                "timestamp TIMESTAMP NOT NULL DEFAULT NOW()," +
                "PRIMARY KEY (level, iteration));"
            );
            stmt.close();
            
            con.commit();
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            if (stmt != null) {
                try {
                    stmt.close();
                } catch (SQLException e) {
                    e.printStackTrace();
                }
            }
            if (con != null) {
                con.setAutoCommit(true);
                releaseConnection(con);
            }
        }
    }
}
